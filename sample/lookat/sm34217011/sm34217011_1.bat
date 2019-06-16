@rem 全ての親を移動したvmdを作成
@rem 事前にsozaiディレクトリを作成し、モーションファイルをコピーしておく
@set VGPATH=..\..\..\vmdgadgets
@set ORIG_MOTION="sozai\ドラマツルギー.vmd"

python %VGPATH%\move_root.py %ORIG_MOTION% --pos 4 0 0 --angles 0 170 0 > yahagi_base.vmd
python %VGPATH%\move_root.py %ORIG_MOTION% --pos -4 0 0  > yamato_base.vmd
