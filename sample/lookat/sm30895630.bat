set MODEL="sozai\ぽんぷ長式初音ミク.pmx"
set MOTION_CENTER="sozai\裏表ラバーズ.vmd"
rem 反転、すべての親を+18
set MOTION_CHERRY="sozai\cherry_x18.vmd"
rem 反転、全ての親を-18
set MOTION_SNOW="sozai\snow_x-18.vmd"
set CAMERA="sozai\裏表カメラ_改変.vmd"
set EYES_CONSTRAINT=両目 10 20 0 0.4 0.4 0
set HEAD_CONSTRAINT=頭 45 50 30 1 1 1
set NECK_CONSTRAINT=首 15 10 0 1 1 1
set NECK_BLEND=首 0.2 0.2 0.5
set HEAD_BLEND=頭 0.2 0.2 0.5

REM center
python ..\..\vmdgadgets\trace_camera.py %MODEL% %MOTION_CENTER% %CAMERA% center_head.vmd --constraint %EYES_CONSTRAINT% --constraint %HEAD_CONSTRAINT% --constraint %NECK_CONSTRAINT% --vmd_blend %NECK_BLEND% --vmd_blend %HEAD_BLEND% --frame_range 585 2538 --frame_range 2573 2763 --frame_range 2895 5274 --frame_range 5291 9999
REM right side cherry
python ..\..\vmdgadgets\trace_camera.py %MODEL% %MOTION_CHERRY% %CAMERA% cherry_head.vmd --constraint %EYES_CONSTRAINT% --constraint %HEAD_CONSTRAINT% --constraint %NECK_CONSTRAINT% --vmd_blend %NECK_BLEND% --vmd_blend %HEAD_BLEND% --frame_range 4749 5274 --frame_range 5291 9999
REM left side snow
python ..\..\vmdgadgets\trace_camera.py %MODEL% %MOTION_SNOW% %CAMERA% snow_head.vmd --constraint %EYES_CONSTRAINT% --constraint %HEAD_CONSTRAINT% --constraint %NECK_CONSTRAINT% --vmd_blend %NECK_BLEND% --vmd_blend %HEAD_BLEND% --frame_range 4749 5274 --frame_range 5291 9999
