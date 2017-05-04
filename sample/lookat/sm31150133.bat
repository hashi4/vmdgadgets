@set MODEL_LEFT="sozai\MikuV3_052f.pmx"
@set MODEL_RIGHT="sozai\ルカV4X_37C.pmx"
@set MOTION_RIGHT="sozai\【肩キャンセルモデル用】Kiss me 愛してる右P.vmd"
@set MOTION_LEFT="sozai\【肩キャンセルモデル用】Kiss me 愛してる左P.vmd"
@set CAMERA="sozai\Kiss me 愛してる_camera_ちょっとEdit_2.vmd"
@set MOTION_LEFT_NECK="left_neck.vmd"
@set MOTION_RIGHT_NECK="right_neck.vmd"

@set NECK_CONSTRAINT=--constraint 首 40 50 30 1 1 0.5
@set HEAD_CONSTRAINT=--constraint 頭 0 0 0 1 1 0
@set NECK_BLEND=--vmd_blend 首 0.4 0.5 .8
@set LK_EYE_CONSTRAINT=--constraint 両目 10 30 0 1 1 0

@set FRAME_RANGES=--frame_range 688 1860 --frame_range 1900 2865 --frame_range 2965 5938 --frame_range 6373 9999

python ..\..\vmdgadgets\trace_camera.py %MODEL_LEFT%  %MOTION_LEFT% %CAMERA% %MOTION_LEFT_NECK% %NECK_BLEND% %NECK_CONSTRAINT% %HEAD_CONSTRAINT% %FRAME_RANGES%
python ..\..\vmdgadgets\trace_camera.py %MODEL_RIGHT%  %MOTION_RIGHT% %CAMERA% %MOTION_RIGHT_NECK% %NECK_BLEND% %NECK_CONSTRAINT% %HEAD_CONSTRAINT% %FRAME_RANGES%
timeout 10
