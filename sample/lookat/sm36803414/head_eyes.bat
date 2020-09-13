@rem モデル、モーション、カメラ(高さを0.91倍)をsozai ディレクトリに保存
@rem 本ファイル実行後両目IKをオフにして merged.vmd をモデルに読込む
@rem head.vmd は 両目・頭・首 のみ

@set MODEL=".\sozai\Eunice08mizugi2.pmx"
@set MOTION=".\sozai\極楽上半身2ボーンが長い用.vmd"
@set CAMERA=".\sozai\カメラ（金剛さんで調整）_.91.vmd"

@set EYES_CONST=--constraint 両目 30 40 0 0.8 0.8 0.0
@set HEAD_CONST=--constraint 頭 65 60 45 0.2 0.2 0.0
@SET NECK_CONST=--constraint 首 30 45 25 0.1 0.1 0.0

@set FRAME_RANGES=--frame_range 948 4021 --frame_range 4918 9999
@set OMEGA=--omega 0
@set IGNORE=--ignore2 30 35

@set VGPATH=..\..\..\vmdgadgets
python %VGPATH%\trace_camera.py %MODEL% %MOTION% %CAMERA% head.vmd %NECK_CONST% %HEAD_CONST% %EYES_CONST% --near --vmd_lerp --use_vmd_interpolation %FRAME_RANGES% %OMEGA% %IGNORE%
python %VGPATH%\omit_motion.py -b 頭 -b 首 -b 両目 %MOTION%|python %VGPATH%\merge_vmd.py -i - head.vmd -o merged.vmd


python %VGPATH%\camlight.py %CAMERA% light.vmd --rx 10 --ry 10


