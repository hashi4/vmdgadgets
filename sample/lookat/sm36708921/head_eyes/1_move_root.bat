@set VGPATH=..\..\..\..\vmdgadgets
@set MOTION="..\sozai\‚³‚Æ‚­Ž®éòŠÛ.vmd"

python %VGPATH%\move_root.py %MOTION% yahagi_base.vmd --pos 12.65 0 0 --angles 0 -90 0
python %VGPATH%\move_root.py %MOTION% yamato_base.vmd --pos -12.65 0 0 --angles 0 90 0
