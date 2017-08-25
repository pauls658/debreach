<?php
$DEBREACH_DEBUG = False;
if ($DEBREACH_DEBUG) {
	ini_set('display_errors', 1); error_reporting(E_ALL);
}

// request state variables
if (!isset($__DEBREACH_BUF_TAINTED)) {
	$__DEBREACH_BUF_TAINTED = False; // Is the data in __debreach_filter() tainted
}
if (!isset($__DEBREACH_DATA_COUNT)) {
	$__DEBREACH_DATA_COUNT = 0; // The total number of bytes echo'd so far
}

function d_echo($data) {
	global $__DEBREACH_BUF_TAINTED;
	$__DEBREACH_BUF_TAINTED = True;
	echo $data;	
}

function __debreach_filter($data) {
	// request state variables
	global $DEBREACH_DEBUG, $__DEBREACH_BUF_TAINTED, $__DEBREACH_DATA_COUNT;

    //DEBUG
    $SEP_START="\n#################### (";
    $SEP_END=") ##################\n";
    $TAINTED_STR_FILE="/tmp/debreach_validation/php_tainted_strs";
    //DEBUG

	// If you are wondering, strlen() returns the number bytes in a string, not
	// characters, which is what we want

	if ($DEBREACH_DEBUG && strlen($data) == 0) {
		// no data means respose ended. Put comment w/ data count if we are debugging
		$beg = "<!-- Data count: ";
		$end = " -->";
		$__DEBREACH_DATA_COUNT += strlen($beg) + strlen($end) +
			strlen($__DEBREACH_DATA_COUNT);
		// if the daata count tips to the the next multiple of 10, the count will
		// be off by one in the comment
		return $beg . $__DEBREACH_DATA_COUNT . $end;
	}

	if ($__DEBREACH_BUF_TAINTED) {
		$cur_byte = $__DEBREACH_DATA_COUNT;
		taint_brs($cur_byte, ($cur_byte + strlen($data) - 1));
		// make our local variables accessible to apache

		if ($DEBREACH_DEBUG) {
    		$debug_file = fopen($TAINTED_STR_FILE, "a+");
    		if (!$debug_file)
    			error_log(error_get_last()["message"]);
    		fwrite($debug_file, $data);
    		fwrite($debug_file, $SEP_START . $cur_byte . "," . ($cur_byte + strlen($data) - 1));
    		fwrite($debug_file, $SEP_END);
    		fclose($debug_file);
		}
	}

	$__DEBREACH_DATA_COUNT += strlen($data);
	return $data;
}
// set chunk_size = 1 so buffer flushes on each echo call
ob_start('__debreach_filter', 1);
?>
