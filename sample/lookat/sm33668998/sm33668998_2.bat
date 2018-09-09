@rem お借りしたものをsozaiディレクトリにコピーしておく

@rem 先に1番を実行してから、本ファイルを実行
@rem motion_luka.vmd, motion_miku.vmdが出来上がるので、
@rem MMD上でこれらのモーションを展開

@rem 矢矧 6663 6805 両目リセット
@rem 大和 1493 1590 両目リセット

@set MODEL_MIKU="sozai\ぽんぷ長式矢矧_v.2.pmx"
@set MODEL_LUKA="sozai\ぽんぷ長式大和_v.1.pmx"

@set MOTION_MIKU=miku.vmd
@set MOTION_LUKA=luka.vmd

@set EYES_CONST=--constraint 両目  24 34 0 0.33 0.33 0
@set HEAD_CONST=--constraint 頭 70 60 80 0.2 0.2 0
@set NECK_CONST=--constraint 首 90 90 90 0 0 0

@set FRAME_RANGES=--frame_range 325 4816 --frame_range 5125 9999
@set IGNORE=--ignore 70

@set VGPATH=..\..\..\vmdgadgets
python %VGPATH%\trace_model.py %MODEL_MIKU% %MOTION_MIKU% %MODEL_LUKA% %MOTION_LUKA% head_miku.vmd %NECK_CONST% %HEAD_CONST% %EYES_CONST% --near --vmd_lerp --use_vmd_interpolation %FRAME_RANGES% %IGNORE%
python %VGPATH%\omit_motion.py -b 頭 -b 首 -b 両目 %MOTION_MIKU%|python %VGPATH%\merge_vmd.py -i - head_miku.vmd -o motion_miku.vmd

python %VGPATH%\trace_model.py %MODEL_LUKA% %MOTION_LUKA% %MODEL_MIKU% %MOTION_MIKU% head_luka.vmd %NECK_CONST% %HEAD_CONST% %EYES_CONST% --near --vmd_lerp --use_vmd_interpolation %FRAME_RANGES% %IGNORE%
python %VGPATH%\omit_motion.py -b 頭 -b 首 -b 両目 %MOTION_LUKA%|python %VGPATH%\merge_vmd.py -i - head_luka.vmd -o motion_luka.vmd
