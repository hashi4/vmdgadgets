@set MODEL_YAMATO="..\sozai\‚Û‚ñ‚Õ’·Ž®‘å˜a_v.1.pmx"
@set MODEL_YAHAGI="..\sozai\‚Û‚ñ‚Õ’·Ž®–î”Š_v.2.pmx"

@set MOTION_YAHAGI=yahagi_base.vmd
@set MOTION_YAMATO=yamato_base.vmd

@set EYES_CONST=--constraint —¼–Ú  24 34 0 0.33 0.33 0
@set HEAD_CONST=--constraint “ª 65 70 35 0.2 0.2 0
@set NECK_CONST=--constraint Žñ 50 50 35 0.2 0.2 0

@set IGNORE=--ignore2 35 45
@set FRAME_RANGES=--frame_range 369 9999

@set VGPATH=..\..\..\..\vmdgadgets

python %VGPATH%\trace_model.py %MODEL_YAHAGI% %MOTION_YAHAGI% %MODEL_YAMATO% %MOTION_YAMATO% head_yahagi.vmd %NECK_CONST% %HEAD_CONST% %EYES_CONST% --near --vmd_lerp --use_vmd_interpolation %FRAME_RANGES% %IGNORE% %ADD_FRAMES%
python %VGPATH%\omit_motion.py -b “ª -b Žñ -b —¼–Ú %MOTION_YAHAGI%|python %VGPATH%\merge_vmd.py -i - head_yahagi.vmd %MORPH% -o yahagi.vmd

python %VGPATH%\trace_model.py %MODEL_YAMATO% %MOTION_YAMATO% %MODEL_YAHAGI% %MOTION_YAHAGI% head_yamato.vmd %NECK_CONST% %HEAD_CONST% %EYES_CONST% --near --vmd_lerp --use_vmd_interpolation %FRAME_RANGES% %IGNORE% %ADD_FRAMES%
python %VGPATH%\omit_motion.py -b “ª -b Žñ -b —¼–Ú %MOTION_YAMATO%|python %VGPATH%\merge_vmd.py -i - head_yamato.vmd %MORPH% -o yamato.vmd
