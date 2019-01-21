<?php
$DEBREACH_DEBUG = False;
if ($DEBREACH_DEBUG) {
	ini_set('display_errors', 1); error_reporting(E_ALL);
}

function debreach_taint($str) {
	//if (in_array("mod_deflate", apache_get_modules())) {
	//	return $str;
	//} else {
		if ($str) { //make sure string is not empty/null
			return "BPBPBPB{" . $str . "BPBPBPB}";
		} else {
			return $str;
		}
	//}
}

function debreach_remove_markers($buf) {
	$marker = "BPBPBPB";
	$outbuf = "";
	$stack = 0;
	$last = 0;
	$brs = [];

	while (true) {
		$match_loc = strpos($buf, $marker, $last); // 8 is length of $marker
		if ($match_loc === FALSE)
			break;

		$outbuf .= substr($buf, $last, $match_loc - $last);
		$last = $match_loc + 8;

		if ($buf[$match_loc + 7] == "{") {
			if ($stack == 0)
				$brs[] = strlen($outbuf);
			$stack += 1;
		} else {
			$stack -= 1;
			if ($stack == 0) {
				$brs[] = strlen($outbuf) - 1;
			} else if ($stack < 0) {
				error_log("DEBREACH: stack was negative");
			}
		}
	}
	if ($last < strlen($buf))
		$outbuf .= substr($buf, $last);
	if ($stack != 0) {
		error_log("DEBREACH: stack was not empty!");
	}
	return $outbuf;
}

$GLOBALS['DBRT'] = "debreach_taint";

ob_start("debreach_remove_markers");

/*
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
		$ret = taint_brs($cur_byte, ($cur_byte + strlen($data) - 1));
		if (is_string($ret)) {
			error_log($ret);
		}
		$__DEBREACH_BUF_TAINTED = False;

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
 */
?>
