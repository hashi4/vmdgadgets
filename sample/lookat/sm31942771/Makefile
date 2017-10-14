# ms nmake用
TARGETS=left.vmd right.vmd
EXT_MOTION=stage.vmd

ORIG_MOTION=sozai\pdapm4ダンス.vmd
CAMERA=edit\camera.vmd

VGPATH=..\..\..\vmdgadgets

all : $(TARGETS) morph_edited.vmd

# ぶつかり回避調整 => 頭・目モーション作成 => マージ
$(TARGETS) : $(@:.vmd=_base.vmd) $(CAMERA) $(EXT_MOTION) lookat.bat minor_adjust.py
	python minor_adjust.py $(@:.vmd=_base.vmd)
	set CAMERA=$(CAMERA)
	set MOTION=$(@:.vmd=_base.vmd)
	set EXT_MOTION=$(EXT_MOTION)
	set HEAD_MOTION=$(@:.vmd=_head.vmd)
	lookat.bat
	python $(VGPATH)\omit_motion.py -b 頭 -b 首 -b 両目  $(@:.vmd=_base.vmd)|python $(VGPATH)\merge_vmd.py -i - $(@:.vmd=_head.vmd) -o $@

# 左右モーション作成(全ての親移動)
left_base.vmd : pdance_e2.vmd
	python $(VGPATH)\move_root.py --pos -4 0 -5 $** $@
right_base.vmd : pdance_e2.vmd
	python $(VGPATH)\move_root.py --pos 4 0 5 --angle 0 180 0 $** $@

# 全ての親位置を(0, 0, 0)に調整(共通)
#pdance_e2.vmd: edit\pdance_edited.vmd
pdance_e2.vmd: $(ORIG_MOTION)
	python modify_root.py $** > $@

# 表情調整(共通)
morph_edited.vmd:$(ORIG_MOTION)
	python edit_morph.py

# 回転床(外部親)
$(EXT_MOTION) : round_floor.py
	python round_floor.py

