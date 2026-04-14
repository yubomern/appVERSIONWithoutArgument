# CMake generated Testfile for 
# Source directory: C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main
# Build directory: C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/build
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
if(CTEST_CONFIGURATION_TYPE MATCHES "^([Dd][Ee][Bb][Uu][Gg])$")
  add_test(csv_analyzer_test "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/build/test/Debug/test_crash_csv_analyzer.exe" "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/build/crash_simulator/build/crash_report.csv")
  set_tests_properties(csv_analyzer_test PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/CMakeLists.txt;39;add_test;C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Rr][Ee][Ll][Ee][Aa][Ss][Ee])$")
  add_test(csv_analyzer_test "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/build/test/Release/test_crash_csv_analyzer.exe" "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/build/crash_simulator/build/crash_report.csv")
  set_tests_properties(csv_analyzer_test PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/CMakeLists.txt;39;add_test;C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Mm][Ii][Nn][Ss][Ii][Zz][Ee][Rr][Ee][Ll])$")
  add_test(csv_analyzer_test "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/build/test/MinSizeRel/test_crash_csv_analyzer.exe" "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/build/crash_simulator/build/crash_report.csv")
  set_tests_properties(csv_analyzer_test PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/CMakeLists.txt;39;add_test;C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/CMakeLists.txt;0;")
elseif(CTEST_CONFIGURATION_TYPE MATCHES "^([Rr][Ee][Ll][Ww][Ii][Tt][Hh][Dd][Ee][Bb][Ii][Nn][Ff][Oo])$")
  add_test(csv_analyzer_test "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/build/test/RelWithDebInfo/test_crash_csv_analyzer.exe" "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/build/crash_simulator/build/crash_report.csv")
  set_tests_properties(csv_analyzer_test PROPERTIES  _BACKTRACE_TRIPLES "C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/CMakeLists.txt;39;add_test;C:/Users/hp/Desktop/patrikCv/linproc--main/linproc--main/CMakeLists.txt;0;")
else()
  add_test(csv_analyzer_test NOT_AVAILABLE)
endif()
subdirs("crash_simulator")
