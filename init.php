<?php
//require_once 'debreach.php';
$dbr_script_start = microtime(true);

function shutdown_dbr() {
	global $dbr_script_start;
	file_put_contents("/home/brandon/php_res/exec_times", (microtime(true) - $dbr_script_start) . "\n", FILE_APPEND);
}

register_shutdown_function("shutdown_dbr");
