"""
Filename    :   FaiNlpUI.py
Copyright   :   FoundAItion Inc.
Description :   Main user interface widgets
Written by  :   Alex Fedosov
Created     :   06/26/2023
Updated     :   09/26/2023
"""

from kivy.lang import Builder
from kivymd.uix.textfield import MDTextField


main_ui = """

#:kivy 1.0.9

<CustomOneLineListItem>
    id: custom_menu_item
    # MDDropDownItem is misaligned in menu, workaround
    text: "  Theme"
    height: dp(56)
    on_release: self.show_submenu()

<TextViewDialog>
    orientation: "vertical"
    size_hint_y: None
    height: "300dp"
    MDScrollView:
        size_hint_y: None
        height: '290dp'
        do_scroll_x: False
        do_scroll_y: True
        MDLabel:
            id: text_content
            text: ''
            disabled: True
            markup: True
            size_hint_y: None
            height: '1500dp'

RootWidget:
    MDBoxLayout:
        id: top_layout
        orientation: 'vertical'
        MDTopAppBar:
            id: toolbar
            title: 'FoundAItion Natural Language Processor, v 1.2.15'
            left_action_items: [["menu", lambda x: app.callback(x)]]

        MDBoxLayout:
            id: logo_layout
            orientation: 'vertical'
            Image:
                id: tuning_panel_image
                source: './data/fai.png'
                pos_hint: {'top': 0.1, 'right': 0.99}
                size_hint: .2, .13
                fit_mode: 'scale-down'
            
            MDBottomNavigation:
                id: bottom_pane
                MDBottomNavigationItem:
                    name: 'TuningPanel'
                    text: 'Tuning'
                    icon: './data/tab_folders.png'

                    MDBoxLayout:
                        orientation: 'vertical'
                        GridLayout:
                            cols: 2
                            spacing: '8dp'
                            size_hint: .8, None
                            height: self.minimum_height
                            MDLabel:
                                text: '[b]Website[/b]'
                                halign: 'center'
                                markup: True
                            MDTextField:
                                id: ingestion_url
                                text: ''
                                hint_text: 'www.company.com'
                                size_hint_y: None
                                height: '30dp'
                            MDLabel:
                                text: '[b]Folder[/b]'
                                halign: 'center'
                                markup: True
                            MDTextField:
                                id: ingestion_folder
                                text: ''
                                hint_text: 'c:/Users'
                                size_hint_y: None
                                height: '30dp'
                            MDLabel:
                                text: '[b]Tag[/b]'
                                halign: 'center'
                                markup: True
                            MDTextField:
                                id: ingestion_tag
                                text: ''
                                hint_text: 'Company'
                                size_hint_y: None
                                height: '30dp'
                            MDLabel:
                                text: ''
                            MDLabel:
                                text: ''
                            MDLabel:
                                text: '[b]Status[/b]'
                                halign: 'center'
                                markup: True
                            MDLabel:
                                id: ingest_status
                                text: 'Ready for in-context learning'
                        FloatLayout:
                            MDRoundFlatButton:
                                text: 'Ingest'
                                pos_hint: {'top': 0.2, 'right': 0.15}
                                size_hint: .1, .1
                                on_release: root.ingest(*args)
                            MDRoundFlatButton:
                                text: 'Reset'
                                pos_hint: {'top': 0.2, 'right': 0.3}
                                size_hint: .1, .1
                                on_release: root.reset(*args)

                MDBottomNavigationItem:
                    name: 'LearningDialog'
                    text: 'Learning'
                    icon: './data/tab_cloud.png'

                    MDBoxLayout:
                        orientation: 'vertical'
                        GridLayout:
                            cols: 2
                            spacing: '3dp'
                            size_hint: .95, .7
                            height: self.minimum_height
                            MDLabel:
                                text: '[b]Prompt[/b]'
                                halign: 'center'
                                markup: True
                                size_hint: None, None
                                width: '100dp'
                            MDTextFieldRect:
                                id: ai_prompt
                                text: ''
                                size_hint_y: None
                                height: '100dp'
                            MDLabel:
                                text: '[b]Response[/b]'
                                halign: 'center'
                                markup: True
                                size_hint: None, None
                                width: '100dp'
                            MDScrollView:
                                size_hint_y: None
                                height: '200dp'
                                do_scroll_x: False
                                do_scroll_y: True
                                MDTextFieldRect:
                                    size_hint_y: None
                                    height: '1000dp'
                                    id: ai_response
                                    text: ''
                                    disabled: True
                            MDLabel:
                                text: '[b]Status[/b]'
                                halign: 'center'
                                markup: True
                                size_hint: None, None
                                height: '50dp'
                                width: '100dp'
                            MDLabel:
                                id: prompt_status
                                text: 'Ready'
                                size_hint_y: None
                                height: '50dp'
                            MDLabel:
                                text: '[b]Use context[/b]'
                                markup: True
                                valign: 'center'
                                size_hint: None, None
                                width: '100dp'
                                height: '50dp'
                            MDBoxLayout:
                                orientation: 'horizontal'
                                size_hint_y: None
                                height: '100dp'
                                MDCheckbox:
                                    id: prompt_use_in_context
                                    size_hint: None, None
                                    size: "50dp", "50dp"
                                MDLabel:
                                    text: '[b]Keep history[/b]'
                                    markup: True
                                    size_hint: None, None
                                    pos_hint: {'top': 0.45}
                                    width: '100dp'
                                MDCheckbox:
                                    id: prompt_keep_history
                                    size_hint: None, None
                                    size: "50dp", "50dp"
                                FloatLayout:
                                    size_hint_y: None
                                    height: '50dp'
                                    Button:
                                        background_normal: './data/learn_running_grey.png'
                                        background_down: './data/learn_running_black.png'
                                        pos_hint: {'right': 0.1, 'top': 0.8}
                                        size_hint: None, None
                                        height: '35dp'
                                        width: '35dp'
                                        fit_mode: 'scale-down'
                                        on_release: root.run(True)
                                    Button:
                                        background_normal: './data/learn_camera_grey.png'
                                        background_down: './data/learn_camera_black.png'
                                        pos_hint: {'right': 0.2, 'top': 0.8}
                                        size_hint: None, None
                                        height: '35dp'
                                        width: '35dp'
                                        fit_mode: 'scale-down'
                                        on_release: root.image_input(*args)
                                    ToggleButton:
                                        id: voice_play
                                        background_normal: './data/learn_voice_grey.png'
                                        background_down: './data/learn_voice_black.png'
                                        pos_hint: {'right': 0.3, 'top': 0.8}
                                        size_hint: None, None
                                        height: '35dp'
                                        width: '35dp'
                                        fit_mode: 'scale-down'
                                        on_release: root.voice_play(*args)
                                    Button:
                                        background_normal: './data/learn_microphone_grey.png'
                                        background_down: './data/learn_microphone_black.png'
                                        pos_hint: {'right': 0.4, 'top': 0.8}
                                        size_hint: None, None
                                        height: '35dp'
                                        width: '35dp'
                                        fit_mode: 'scale-down'
                                        on_release: root.voice_input(*args)

                MDBottomNavigationItem:
                    name: 'Graph'
                    text: 'Graph'
                    icon: './data/tab_bolt.png'

                    MDBoxLayout:
                        orientation: 'vertical'
                        MDBoxLayout:
                            id: main_graph_widget

                MDBottomNavigationItem:
                    name: 'settings'
                    text: 'Settings'
                    icon: './data/tab_scroll.png'
                    
                    MDBoxLayout:
                        orientation: 'vertical'            
                        GridLayout:
                            cols: 2
                            size_hint: .8, .4
                            height: self.minimum_height
                            MDLabel:
                                text: '[b]Audio[/b]'
                                halign: 'center'
                                markup: True
                            MDTextField:
                                id: audio_model
                                text: 'vosk-model-small-en-us-0.15'
                                hint_text: 'Audio model'
                            MDLabel:
                                text: '[b]Image[/b]'
                                halign: 'center'
                                markup: True
                            MDTextField:
                                id: image_model
                                text: 'ViT-B-32.pt'
                                hint_text: 'Image model'
                            MDLabel:
                                text: '[b]LLM[/b]'
                                halign: 'center'
                                markup: True
                            MDTextField:
                                id: ai_model
                                text: 'gpt-4'  # gpt-3.5-turbo / gpt-4
                                hint_text: 'LLM model, use gpt-4 or gpt-3.5-turbo'
                            MDLabel:
                                text: '[b]Embedding[/b]'
                                halign: 'center'
                                markup: True
                            MDTextField:
                                id: embedding_model
                                text: 'text-embedding-ada-002'
                                hint_text: 'Embedding model'
                            MDLabel:
                                text: '[b]Database[/b]'
                                halign: 'center'
                                markup: True
                            MDTextField:
                                id: embedding_database
                                text: 'fai-rag-db'
                                hint_text: 'Embedding database'
                            MDLabel:
                                text: '[b]Temperature[/b]'
                                halign: 'center'
                                markup: True
                            MDSlider:
                                id: ai_temperature
                                text: '0'
                                min: 0
                                max: 1
                                value: .0
                                step: .1
                                height: '30dp'
                                hint: True
                                size_hint_y: None
                                on_value: root.change_temperature(*args)
                        FloatLayout:
                            MDRoundFlatButton:
                                id: general_settings
                                text: 'Save'
                                pos_hint: {'top': 0.15, 'right': 0.25}
                                size_hint: .1, .1
                                on_release: root.save_settings(*args)
                                text_color: app.theme_cls.primary_color
                                line_color: app.theme_cls.primary_color

"""

def LoadMainUIFromString():
    return Builder.load_string(main_ui)