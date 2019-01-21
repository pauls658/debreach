<?php
function rutime($ru, $rus, $index) {
	    return ($ru["ru_$index.tv_sec"]*1000 + intval($ru["ru_$index.tv_usec"]/1000))
			     -  ($rus["ru_$index.tv_sec"]*1000 + intval($rus["ru_$index.tv_usec"]/1000));
}

$ru = getrusage();
//echo "This process used " . rutime($ru, $rustart, "utime") .
//	    " ms for its computations\n";
//echo "It spent " . rutime($ru, $rustart, "stime") .
//	    " ms in system calls\n";
file_put_contents("/home/brandon/php_res/exec_times", (microtime(true) - $dbr_script_start) . "\n", FILE_APPEND);
//file_put_contents("/home/brandon/php_res/user_times", (rutime($ru, $rustart, "utime")) . "\n", FILE_APPEND);
