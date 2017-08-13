@set CAMERA=suki_yuki_maji_magic_cam.vmd
@IF NOT EXIST %CAMERA% python sm31702815_camera.py

@set MODEL="sozai\静謐のハサン.pmx"
@set MOTION="sozai\好き雪本気マジック_Lat式.vmd"
@set OUT_VMD=suki_yuki_maji_magic_head.vmd

@set NECK_CONST=--constraint 首 10 10 10 0.1 0.1 0
@set HEAD_CONST=--constraint 頭 40 60 40 0.4 0.3 0
@set EYES_CONST=--constraint 両目 10 20 0 0.55 0.4 0
@set ADD_FRAMES= --add_frames 55
@set FRAME_RANGES= --frame_range 0 401 --frame_range 430 1388 --frame_range 1421 1595 --frame_range 1631 1655 --frame_range 1681 1987 --frame_range 2030 3106 --frame_range 3152 3314 --frame_range 3356 3376 --frame_range 3407 3713 --frame_range 3754 4874 --frame_range 4909 4921 --frame_range 4987 5263 --frame_range 5308 9999

python ..\..\vmdgadgets\trace_camera.py %MODEL% %MOTION% %CAMERA% %OUT_VMD% %NECK_CONST% %HEAD_CONST% %EYES_CONST% %ADD_FRAMES% %FRAME_RANGES% --near --vmd_lerp
