@rem お借りしたものをsozaiディレクトリへコピーしておく
@rem 1番実行後、本ファイルを実行

@set VGPATH=..\..\..\vmdgadgets

@set EYES_CONST=--constraint 両目 9.0 15.0 0.0 0.2 0.2 0.0
@set HEAD_CONST=--constraint 頭 80 60 80 0.3 0.3 0
@set NECK_CONST=--constraint 首 80 60 80 0.1 0.1 0

@rem カメラはお借りしたものを X:-3, Z:-2 してます
@set CAMERA="sozai\帝国少女　カメラ.vmd"
@set FRAME_RANGES=--frame_range 0 4884  --frame_range 5975 9999

@set MODEL_KONGO="sozai\金剛改二(艤装なし).pmx"

@set TARGET=金剛
@set MODEL=%MODEL_KONGO%
@set MOTION=1.vmd
call :GAZE

@set TARGET=比叡
@set MODEL_HIEI="sozai\比叡改二(艤装なし).pmx"
@set MOTION=2.vmd
@set MODEL=%MODEL_HIEI%
call :GAZE

@set TARGET=榛名
@set MODEL="sozai\榛名改二(艤装なし).pmx"
@set MOTION=3.vmd
call :GAZE

@rem 霧島
@set MODEL="sozai\霧島改二(艤装なし).pmx"
@set TARGET=霧島
@set MOTION=4.vmd
call :GAZE

exit /b

:GAZE
python %VGPATH%\trace_camera.py %MODEL% %MOTION% %CAMERA% %TARGET%_head.vmd %NECK_CONST% %HEAD_CONST% %EYES_CONST% --near --vmd_lerp --use_vmd_interpolation %FRAME_RANGES% %IGNORE% %TRIM%
python %VGPATH%\omit_motion.py -b 頭 -b 首 -b 両目 %MOTION%|python %VGPATH%\merge_vmd.py -i - %TARGET%_head.vmd -o %TARGET%.vmd
