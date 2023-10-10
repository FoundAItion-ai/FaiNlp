
rem  ************** NOTE: add to FaiNlpProductFull.wxs:  ************** 
rem  .
rem  <?define FaiReleasePath=C:\Info\Projects\Docs\FoundAItion\Source\Samples\dmalex\dist\FaiNlp ?>
rem  after <Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
rem  .
rem  and in VS build Release/x86
rem  .
rem  ******************************************************************


C:\Info\Projects\Docs\FoundAItion\Source\Samples\setup\packages\WixToolset.Heat.4.0.1\tools\net472\x64\heat dir C:\Info\Projects\Docs\FoundAItion\Source\Samples\dmalex\dist\FaiNlp\ -var FaiReleasePath -dr INSTALLFOLDER -ke -srd -cg ProductComponents -gg -sfrag -suid -out "FaiNlpProductFull.wxs"