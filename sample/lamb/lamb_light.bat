set CAMERA=%1
set SCRIPT_PATH=..\..\vmdgadgets
python %SCRIPT_PATH%\camlight.py %CAMERA% --rgb .5 .5 .5  > 1.vmd
python %SCRIPT_PATH%\camlight.py %CAMERA% --against --rx --rgb .5 .5 .5  > 2.vmd
python %SCRIPT_PATH%\camlight.py %CAMERA%  --rx 5 --ry 60 --rgb .5 .5 .5> 3.vmd
python %SCRIPT_PATH%\camlight.py %CAMERA%  --rx 50 --rgb .5 .5 .5> 4.vmd
python %SCRIPT_PATH%\vmd_concat.py < lamb_light_concat.txt > light.vmd
