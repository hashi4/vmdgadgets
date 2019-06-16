@rem 全ての親を移動したvmdを作成
@rem 事前にsozaiディレクトリを作成し、モーションファイルをコピーしておく
@set VGPATH=..\..\..\vmdgadgets
@set ORIG_MOTION="sozai\VALENTI.vmd"

python %VGPATH%\move_root.py %ORIG_MOTION% --pos 3.15 0 0 --angles 0 -160 0 > yahagi_base.vmd
python %VGPATH%\move_root.py %ORIG_MOTION% --pos -3 0 0 --angles 0 20 0 > yamato_base.vmd

@rem 「お」の大きさ調整
@set PYTHONPATH=%PYTHONPATH%;%VGPATH%
python uo.py
