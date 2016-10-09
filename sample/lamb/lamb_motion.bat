set SCRIPT_PATH=..\..\vmdgadgets
python %SCRIPT_PATH%\stepback.py %1|python %SCRIPT_PATH%\transmotion.py --leftfoot 0.81161 1.10705 -0.141082 --ry -36 --scale 0.8 --offset -3 0 8.5 >2nd_motion.vmd
