@set VGPATH=..\..\..\vmdgadgets

@set CAMERA="sozai\íÈçëè≠èóÅ@ÉJÉÅÉâ.vmd"
python %VGPATH%\camlight.py %CAMERA% light1.vmd --rx -10 --ry 10 --auto_add_frames
python %VGPATH%\camlight.py %CAMERA% light2.vmd --ry 70 --against --auto_add_frames
python %VGPATH%\camlight.py %CAMERA% light3.vmd --ry 10 --against --auto_add_frames

python %VGPATH%\vmd_concat.py light_def.txt light.vmd
