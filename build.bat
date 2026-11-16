@echo off
rem Build AdminFilter.asi (32-bit) with llvm-mingw / mingw-w64 i686
setlocal
cd /d "%~dp0"
set CXX=i686-w64-mingw32-g++
set CC=i686-w64-mingw32-gcc
set MH=third_party\minhook
if not exist build mkdir build

%CC% -O2 -c %MH%\src\buffer.c      -I%MH%\include -o build\buffer.o      || goto :err
%CC% -O2 -c %MH%\src\hook.c        -I%MH%\include -o build\hook.o        || goto :err
%CC% -O2 -c %MH%\src\trampoline.c  -I%MH%\include -o build\trampoline.o  || goto :err
%CC% -O2 -c %MH%\src\hde\hde32.c   -I%MH%\include -o build\hde32.o       || goto :err

%CXX% -O2 -s -std=c++17 -shared -static -static-libgcc -static-libstdc++ ^
  -I%MH%\include asi\src\main.cpp build\buffer.o build\hook.o build\trampoline.o build\hde32.o ^
  -o build\AdminFilter.asi -Wl,--kill-at || goto :err

copy /y config\AdminFilter.ini build\AdminFilter.ini >nul
echo.
echo [OK] build\AdminFilter.asi
exit /b 0
:err
echo [FAILED]
exit /b 1
