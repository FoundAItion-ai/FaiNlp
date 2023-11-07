"""
Filename    :   FaiNlp.py
Copyright   :   FoundAItion Inc.
Description :   Application entry point and UI classes
Written by  :   Alex Fedosov
Created     :   06/26/2023
Updated     :   10/16/2023
"""

try:
    pyi_splash = None
    import pyi_splash
    import os
    os.environ["KIVY_NO_CONSOLELOG"] = "1"
    os.environ["KIVY_NO_FILELOG"] = "1"
except ImportError:
    pass

from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.resources import resource_add_path, resource_find
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.button import MDRoundFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.dropdownitem import MDDropDownItem
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import MDSnackbar

from PIL import Image as PilImage

from FaiCommon.OAIAccess import OpenAIAccess
from FaiCommon.RAGManager import RAGManager
from FaiNlpUI import LoadMainUIFromString
from FaiNlpLicense import License

import base64
import ctypes
import gc
import json
import io
import faulthandler
import numpy as np
import os
import plotly.graph_objects as gobj
import re
import sys
import time
import traceback


Window.size = (1000, 700)


class FeatureFlags:
    FULL_VERSION = True
    IMAGE_RECOGNITION = False
    VOICE_RECOGNITION = False

    def __init__(self, *args, **kwargs):
        if FeatureFlags.FULL_VERSION:
            FeatureFlags.IMAGE_RECOGNITION = True
            FeatureFlags.VOICE_RECOGNITION = True
        else:
            print("Lightweight application version, no voice or image recognition")


if FeatureFlags.FULL_VERSION:
    from FaiCommon.VoiceCog import VoiceCog, VoicePlayerAsync
    from FaiCommon.ImageCog import ImageCog


class TextViewDialog(BoxLayout):
    def __init__(self, *args, **kwargs):
        if "text_content" in kwargs:
            self.text_content = kwargs["text_content"]
            del kwargs["text_content"]
        super().__init__(*args, **kwargs)

    def on_kv_post(self, base_widget):
        self.ids.text_content.text = self.text_content


class CustomOneLineListItem(MDDropDownItem):
    COLOR_SCHEME = [
        "Red", "Pink", "Purple", "DeepPurple", "Indigo", "Blue", "LightBlue", "Cyan", "Teal", "Green", "LightGreen", "Lime", "Yellow", "Amber", "Orange", "DeepOrange", "Brown", "Gray", "BlueGray"
    ]

    def __init__(self, *args, **kwargs):
        submenu_items = [{
                    "viewclass": "OneLineListItem", 
                    "height": dp(56), 
                    "text": CustomOneLineListItem.COLOR_SCHEME[i],
                    "on_release": lambda x=i: self.menu_callback(x),
                } for i in range(len(CustomOneLineListItem.COLOR_SCHEME))
            ]
        self.submenu = MDDropdownMenu(
            items=submenu_items,
            width_mult=4,
        )

        super().__init__(*args, **kwargs)

    def show_submenu(self):
        self.submenu.caller = self
        self.submenu.open()

    def menu_callback(self, item):
        self.submenu.dismiss()
        MDApp.get_running_app().change_theme(CustomOneLineListItem.COLOR_SCHEME[item])


class RootWidget(MDScreen):

    # maybe use .pydantic to simplify schema construction?
    #
    # =======>         https://jsonlint.com           <=======
    # =======> Also DO VALIDATE JSON before execution <=======
    # =======>                                        <=======
    #
    FN_DECLARATION = [
        {
            "name": "ShowMeGraph",
            "description": "Show a graph of numbers in array",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "number"
                        },
                        "description": "array of numbers"
                    },
                    "style": {
                        "type": "string", 
                        "enum": ["bar", "plot", "scatter"]
                    }
                },
                "required": ["data"]
            }
        },
        {
            "name": "VisualizeObject",
            "description": "Show or present visually or draw an object with this description",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Object description"
                    }
                },
                "required": ["description"]
            }
        },
        {
            "name": "LoadData",
            "description": "Load or get or fetch or retrieve data from local, corporate's storage",
            "parameters": {
                "type": "object",
                "properties": {
                    "datatype": {
                        "type": "string",
                        "description": "What type of data should be loaded from local corporate's data storage"
                    }
                },
                "required": ["datatype"]
            }
        }
    ]
    # or
    #"description": "Load or get or fetch or retrieve a data of this type only - price, salary, amount",
    #"enum": ["price", "salary", "amount"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.app_path = os.path.abspath(".")
        self.voice_cog = None
        self.image_cog = None
        self.voice_player = None

        gc.set_debug(gc.DEBUG_STATS)
        # gc.set_debug(gc.DEBUG_SAVEALL)
        print("GC debugging is on", file=sys.stderr)
        gc.disable()

    def stop(self):
        if self.voice_player is not None:
            self.voice_player.stop()
        os._exit(0)

    def on_kv_post(self, base_widget):
        # PyInstaller startup splash screen (availably from .EXE only)
        # can also check with pyi_splash is not None:
        if getattr(sys, 'frozen', False):
            pyi_splash.close()
            # Pyinstaller bundle, --add-data
            self.app_path = sys._MEIPASS
            resource_add_path(self.app_path)
            resource_add_path(os.path.join(self.app_path, "resources"))
            self.ids.tuning_panel_image.source = resource_find(r"data\fai.png")

        ai_model = self.ids.ai_model.text
        audio_model = self.ids.audio_model.text
        image_model = self.ids.image_model.text
        embedding_model = self.ids.embedding_model.text
        ai_temperature = self.ids.ai_temperature.value

        self.oai_access = OpenAIAccess(ai_model, ai_temperature, embedding_model)
        self.main_graph = Image()
        self.rag_manager = None

        if FeatureFlags.FULL_VERSION:
            self.voice_cog = VoiceCog(audio_model)
            self.image_cog = ImageCog(image_model)
            self.voice_player = VoicePlayerAsync(name="Zira")
        else:
            self.ids.audio_model.disabled = True
            self.ids.image_model.disabled = True
        
        self.ids.main_graph_widget.add_widget(self.main_graph)
        Window.bind(on_key_up=self.on_key_up)

    def on_key_up(self, instance, keyboard, keycode):
        # TODO(afedosov): also check if we hit Enter when at the end of the line
        if self.ids.ai_prompt.focused and keyboard == 13:  # Enter
            self.run(False)

    def _create_rag_manager(self):
        ai_model = self.ids.ai_model.text
        embedding_model = self.ids.embedding_model.text
        embedding_database = Main.get_data_path(self.ids.embedding_database.text)
        self.rag_manager = self.rag_manager or RAGManager(ai_model, embedding_model, embedding_database)

    def _open_rag_manager(self):
        count = self.rag_manager.open()
        self.ids.ingest_status.text = f"Storage initialized, loaded {count} pages"

    def save_settings(self, *args):
        ai_temperature = self.ids.ai_temperature.value
        if not self.oai_access.set_temperature(ai_temperature):
            self.ids.general_settings.text = f"Not Saved"
            Clock.schedule_once(self._restore_settings_page, 3)
            return

        ai_model = self.ids.ai_model.text
        ai_models = self.oai_access.get_models()['data']
        found = False

        for index in range(len(ai_models)):
            if ai_model == ai_models[index]['id']:
                found = True
                break

        if found:
            self.oai_access.set_model(ai_model)
            self.ids.general_settings.text = f"Saved"
        else:
            self.ids.general_settings.text = f"Not Saved"
        Clock.schedule_once(self._restore_settings_page, 3)

    def _restore_settings_page(self, *args):
        self.ids.general_settings.text = f"Save"

    def ingest(self, *args):
        ingestion_folder = self.ids.ingestion_folder.text
        ingestion_url = self.ids.ingestion_url.text
        self._create_rag_manager()

        if not ingestion_folder and not ingestion_url:
            self._open_rag_manager()
            return

        MDSnackbar(MDLabel(text="Data ingestion is in progress...")).open()

        if ingestion_folder:
            ok, status = self.rag_manager.ingest_from_folder(ingestion_folder)
        else:
            ok, status = self.rag_manager.ingest_from_web(ingestion_url, max_depth=2)

        if not ok:
            self.ids.ingest_status.text = f"Storage error: {status}"
        else:
            self.ids.ingest_status.text = f"Loaded {status} page(s)"

    def voice_play(self, *args):
        if self.voice_cog is None:
            MDSnackbar(MDLabel(text="Voice play is not available in this version")).open()
        elif self.ids.voice_play.state == "down":
            MDSnackbar(MDLabel(text="Voice play is enabled")).open()
    
    def voice_input(self, *args):
        if self.voice_cog is None:
            MDSnackbar(MDLabel(text="Voice input is not available in this version")).open()
            return
            
        try:
            self.ids.ai_prompt.text = self.voice_cog.listen()
            self.ids.ai_prompt.canvas.ask_update()
            self.run(None)
        except:
            self.ids.ingest_status.text = "Voice recognition failed"
 
    def change_temperature(self, *args):
        # Not needed for slider, may be for status update?
        pass

    def image_input(self, *args):
        if self.image_cog is None:
            MDSnackbar(MDLabel(text="Image recognition is not available in this version")).open()
            return
        
        ai_prompt = self.ids.ai_prompt.text.strip()
        texture = self.main_graph.texture
        if texture is None:
            self.ids.prompt_status.text = "No image provided"
            return
        if not ai_prompt:
            self.ids.prompt_status.text = "No image description provided"
            return

        # convert kivy.uix.image.Image to PIL image
        MDSnackbar(MDLabel(text="Image recognition is in progress")).open()
        image_data = np.frombuffer(texture.pixels, dtype=np.uint8)
        image_data = np.reshape(image_data, (texture.height, texture.width, 4))
        # Kivy images are in BGR format, so we need to convert to RGB, swap color channels
        image_data = image_data[:, :, [2, 1, 0]]
        pil_image = PilImage.fromarray(image_data)

        # Don't use NLP for this request, although we might :)
        labels = list(set(re.split(r'\W+', ai_prompt)))
        common_labels = ["", "is", "it", "this", "that", "or", "are", "these", "those", "a", "an", "the"]
        for common_label in common_labels:
            if common_label in labels:
                labels.remove(common_label)

        if not labels:
            self.ids.prompt_status.text = f"Invalid image description provided"
            return

        result, probability, result_verbose = self.image_cog.recognize(pil_image, labels)

        if not result:
            self.ids.ai_response.text = f""
            self.ids.prompt_status.text = f"Image recognition failed"
        elif probability > 50:
            self.ids.ai_response.text = result_verbose
            self.ids.prompt_status.text = result
        else:
            self.ids.ai_response.text = result_verbose
            self.ids.prompt_status.text = f"Not recognized"

    def reset(self, *args):
        MDSnackbar(MDLabel(text="Database reset is in progress...")).open()
        self._create_rag_manager()
        count = self.rag_manager.reset()
        self.ids.ingest_status.text = f"Reset is complete, {count} record(s) removed"

    def visualize_object(self, description):
        if not description:
            return "No description"
        
        image_str = self.oai_access.create_image(description)
        if not image_str:
            return "No image generated"
        
        image_binary = base64.b64decode(image_str)
        return self.show_image(image_binary)

    def show_image(self, image_binary):
        try:
            image_data = io.BytesIO(image_binary)
            image_texture = CoreImage(image_data, ext="png").texture
            
            self.ids.main_graph_widget.remove_widget(self.main_graph)
            self.main_graph = Image(texture=image_texture)
            self.ids.main_graph_widget.add_widget(self.main_graph)
            image_data.close()
        except Exception as err:
            return "Image generation error {}".format(str(err))
        return "Complete"
        
    def handle_fn_call(self, fn_name, fn_args) -> tuple((str, str)):
        # TODO(afedosov): Validate JSON
        arguments = json.loads(fn_args)
        match fn_name:
            case "LoadData":
                datatype = arguments["datatype"]
                # if datatype not in ["price", "salary", "amount"]:
                #    raise Exception(f"Function {fn_name} is not called, wrong data type: {datatype}")
                
                file_name = os.path.join(self.app_path, r".\demo\DemoData.txt")
                if not os.path.isfile(file_name):
                    raise Exception(f"Function {fn_name} is not called, file {file_name} not found")

                with open(file_name) as f:
                    data = f.read()
                return f"Function {fn_name} called", data
            case "VisualizeObject":
                description = arguments["description"]
                result = self.visualize_object(description)
                return f"Function {fn_name} called", result

            case "ShowMeGraph":
                style = arguments["style"] if "style" in arguments else "bar"
                data = arguments["data"]
                if not data:
                    raise Exception(f"Invalid function {fn_name} arguments")
                
                match style:
                    case "bar":
                        trace = gobj.Bar(y=data)
                    case "plot":
                        trace = gobj.Scatter(
                            y=data, 
                            mode="lines", 
                            line=dict(width=8)
                        )
                    case "scatter":
                        trace = gobj.Scatter(
                            y=data, 
                            mode="markers", 
                            marker=dict(size=12, line=dict(width=8))
                        )
        
                self.trace.append(trace)
                return f"Function {fn_name} called",  "Complete"
            case _:
                return f"Function {fn_name} called", "Unknown function"


    def run(self, *args):
        # Use prompt like: 
        # show me plot of all Fibbonachi numbers from 1 to 15
        # or show bar chart of 15 numbers, each one is randomly selected from range 1 to 50
        # or load salary data and show them as a plot
        ai_prompt = self.ids.ai_prompt.text.strip()
        total_tokens = 0
        response = ""
        status = ""

        if not ai_prompt:
            self.ids.prompt_status.text = "Empty prompt"
            self.ids.ai_response.text = ""
            return
        
        # More flexible with "use context" checkbox
        # if self.rag_manager is not None:
        # 
        if self.ids.prompt_use_in_context.active:
            self._create_rag_manager()
            self._open_rag_manager()
            print("Use in-context learning, RAG")
            ok, ai_response = self.rag_manager.query(ai_prompt)
            if ok:
                answer = ai_response["answer"]
                source = ai_response['sources']

                # Maybe file path or url
                if os.path.isfile(source):
                    source = os.path.basename(source)

                if answer.find("I don\'t know") == -1:
                    self.ids.prompt_status.text = f"Source: {source}"
                    self.ids.ai_response.text = answer
                    return

        try:
            self.trace = []

            if args[0]:
                fn_declaration = RootWidget.FN_DECLARATION
                print("Using LLM function-calling")
            else:
                fn_declaration = None

            fn_generator = self.oai_access.complete_with_multi_fun(
                ai_prompt,
                fn_declaration,
                keep_history = self.ids.prompt_keep_history.active
                )
            start_time = time.monotonic()
            result = next(fn_generator)

            while True:
                total_tokens = total_tokens + result.usage_tokens
                if not result.fn_called:
                    status = f"Complete"
                    # say it if there were no previous function calling, pure completion
                    if not response:
                        response = result.response
                        if self.voice_player is not None and self.ids.voice_play.state == "down":
                            self.ids.ai_response.text = response
                            self.ids.ai_response.canvas.ask_update()
                            self.voice_player.play(response)
                    break
                
                response = response + "Call " + result.response + " ( " + result.status + " )\n"
                _, fn_call_result = self.handle_fn_call(result.response, result.status)
                result = fn_generator.send(fn_call_result)

            completion_time = time.monotonic() - start_time
            print(f"OAI call(s) complete in {completion_time:.2f} sec")

            if self.trace:
                fig = gobj.Figure(data=self.trace)
                fig.update_layout(font=dict(size=30))
                self.show_image(fig.to_image("png", width=1400, height=1400))

        except Exception as err:
            response = ""
            status = str(err)

        self.ids.ai_response.text = response
        self.ids.prompt_status.text = f"{status}, {total_tokens} token(s) used"


class FaiNlp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self):
        self.theme_cls.primary_palette = "Orange"
        self.root = LoadMainUIFromString()
        self.dialogAbout = None
        self.dialogLicense = None
        self.box_layout = BoxLayout(orientation='vertical')
        label = Label(text='This is a left-aligned text inside the dialog.',
                            halign='center',
                            valign='center',
                            size_hint_y=None)
        label.padding_x = 20
        label.padding_y = 20
        self.box_layout.add_widget(label)

        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": "About",
                "height": dp(56),
                "on_release": lambda x="About": self.menu_callback(x),
            },
            {
                "viewclass": "OneLineListItem",
                "text": "License",
                "height": dp(56),
                "on_release": lambda x="License": self.menu_callback(x),
            },            
            {
                "viewclass": "CustomOneLineListItem",
            },
            {
                "viewclass": "OneLineListItem",
                "text": "Exit",
                "height": dp(56),
                "on_release": lambda x="Exit": self.menu_callback(x),
            }
        ]

        self.menu = MDDropdownMenu(
                    items=menu_items,
                    width_mult=4,
                )

        return self.root
    
    def on_stop(self, *args):
        self.root.stop()

    def callback(self, button):
        self.menu.caller = button
        self.menu.open()

    def change_theme(self, theme):
        self.menu.dismiss()
        self.theme_cls.primary_palette = theme
        self.root.ids.bottom_pane.text_color = self.theme_cls.primary_color
        self.root.ids.bottom_pane.text_color_active = self.theme_cls.primary_color
        
    def menu_callback(self, text_item):
        self.menu.dismiss()
        match text_item:
            case "About":
                MDSnackbar(MDLabel(text=text_item)).open()
                self.show_about_dialog()
            case "License":
                MDSnackbar(MDLabel(text=text_item)).open()
                self.show_license_dialog()
            case "Exit":
                MDSnackbar(MDLabel(text="Exiting... Good Bye")).open()
                Clock.schedule_once(self.on_stop, 2)

    def show_about_dialog(self):
        self.dialogAbout = self.dialogAbout or MDDialog(
            title="About FaiNlp Application",
            text="\n[b]FAINLP[/b], Natural Language Processing Technology Demonstrator\n\nCopyright [b](c) 2023 FoundAItion[/b]. All Rights Reserved.",
            radius=[30, 14, 30, 14],
            buttons=[
                MDRoundFlatButton(
                    text="Ok",
                    on_release=lambda _: self.dialogAbout.dismiss(),
                ),
            ],
        )
        self.dialogAbout.open()

    def show_license_dialog(self):
        self.dialogLicense = self.dialogLicense or MDDialog(
            title="FaiNlp Application License Agreement",
            type="custom",
            radius=[30, 14, 30, 14],
            content_cls=TextViewDialog(text_content=License()),
            buttons=[
                MDRoundFlatButton(
                    text="Ok",
                    on_release=lambda _: self.dialogLicense.dismiss(),
                ),
            ],
        )
        self.dialogLicense.open()


class Main():
    @staticmethod
    def get_data_path(path):       
        if getattr(sys, "frozen", False):
            app_folder = os.path.join(os.environ.get("LOCALAPPDATA"), "FoundAItion\\FaiNlp")
            if not os.path.exists(app_folder):
                os.makedirs(app_folder)
            return os.path.join(app_folder, path)
        else:
            # Always exists
            return os.path.join(".\\", path)

    @classmethod
    def run(cls):
        try:
            FaiNlp().run()
        except Exception as err:
            ctypes.windll.user32.MessageBoxW(0, traceback.format_exc(), "FoundAItion Message", 0x10 | 0x1)

if __name__ == '__main__':
    log_path = Main.get_data_path("FaiNlp.log")
    with open(log_path, "w+") as f:
        f.write("Initialized\n")
        faulthandler.enable(f)
        Main.run()
        f.write("UnInitialized\n")
