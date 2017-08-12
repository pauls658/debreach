<?php
ini_set('display_errors', 1); error_reporting(E_ALL);

function d_echo($data) {
	$_REQUEST['__DEBREACH_TAINT_BUF'] = True;
	echo $data;	
}

$DEBREACH_DEBUG = False;
if (!array_key_exists('__DEBREACH_DATA_COUNT', $_REQUEST)) {
	$_REQUEST['__DEBREACH_DATA_COUNT'] = 0;
}
if (!array_key_exists('__DEBREACH_TAINT_BUF', $_REQUEST)) {
	$_REQUEST['__DEBREACH_TAINT_BUF'] = False;
}
function __debreach_filter($data) {
    //DEBUG
    $SEP_START="\n#################### (";
    $SEP_END=") ##################\n";
    $TAINTED_STR_FILE="/tmp/debreach_validation/php_tainted_strs";
    //DEBUG

	// If you are wondering, strlen() returns the number bytes in a string, not
	// characters, which is what we want

	if ($DEBREACH_DEBUG && strlen($data) == 0) {
		// respose data ended. Put comment w/ data count if we are debugging
		$beg = "<!-- Data count: ";
		$end = " -->";
		$_REQUEST['__DEBREACH_DATA_COUNT'] += strlen($beg) + strlen($end) +
			strlen($_REQUEST['__DEBREACH_DATA_COUNT']);
		// if the daata count tips to the the next multiple of 10, the count will
		// be off by one in the comment
		return $beg . $_REQUEST['__DEBREACH_DATA_COUNT'] . $end;
	}

	if ($_REQUEST['__DEBREACH_TAINT_BUF']) {
		$cur_byte = $_REQUEST['__DEBREACH_DATA_COUNT'];
		$cur_brs = apache_note("__DEBREACH_BRS");
		if ($cur_brs) {
			// there was already some data
			apache_note("__DEBREACH_BRS", $cur_brs . "," . $cur_byte . "," . ($cur_byte + strlen($data) - 1));
		} else {
			apache_note("__DEBREACH_BRS", $cur_byte . "," . ($cur_byte + strlen($data) - 1));
		} 
		$_REQUEST['__DEBREACH_TAINT_BUF'] = False;

		//DEBUG
		$debug_file = fopen($TAINTED_STR_FILE, "a+");
		if (!$debug_file)
			error_log(error_get_last()["message"]);
		fwrite($debug_file, $data);
		fwrite($debug_file, $SEP_START . $cur_byte . "," . ($cur_byte + strlen($data) - 1));
		fwrite($debug_file, $SEP_END);
		fclose($debug_file);
		//DEBUG
	}

	$_REQUEST['__DEBREACH_DATA_COUNT'] += strlen($data);
	return $data;
}
// set chunk_size = 1 so buffer flushes on each echo call
ob_start('__debreach_filter', 1);
?>
