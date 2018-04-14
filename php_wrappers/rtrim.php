<?php
$open_marker = "{{";
$close_marker = "}}";

function debreach_wrap_rtrim($str, $mask = " \t\n\r\0\x0B") {
	global $open_marker, $close_marker;
	$marker_end = strrpos($str, $close_marker) + strlen($close_marker) - 1;
	if ($marker_end === false)
		return rtrim($str, $mask);

	$set = array();
	for ($i = 0; $i < strlen($mask); $i++)
		$set[$mask[$i]] = 1;

	$close_off = false; // whether we should add a marker to the end after trimming
	$trim_to = 0; // 
	for ($i = strlen($str) - 1; $i >= 0; $i--) {
		if ($i == $marker_end) {
			if ($close_off) {
				// hopping an open marker, find the next close marker
				$marker_end = strrpos($str, $close_marker, $marker_end - strlen($str) - 1);
				if ($marker_end === false) 
					$marker_end = 0;
				else 
					$marker_end += strlen($close_marker) - 1;
				$i -= strlen($open_marker) - 1; // - 1 because we decrement on the next iter
			} else {
				// hopping an close marker, find the next open marker
				$marker_end = strrpos($str, $open_marker, $marker_end - strlen($str) - 1);
				if ($marker_end === false) 
					$marker_end = 0;
				else 
					$marker_end += strlen($open_marker) - 1;
				$i -= strlen($close_marker) - 1; //  -1 because we decrement on the next iter
			}
			$close_off = !$close_off;
		}
		elseif (!array_key_exists($str[$i], $set)) {
			$trim_to = $i;
			break;
		}
	}
	
	$ret = substr($str, 0, $trim_to + 1);
	if ($close_off)
		$ret .= $close_marker;
	return $ret;
}

$om = $open_marker;
$cm = $close_marker;
$TESTS[0] = array("fuck this $om". "place$cm", "ace");
$RESULTS[0] = "fuck this $om" . "pl$cm";
$TESTS[1] = array("fuck this $om". "place$cm", "place");
$RESULTS[1] = "fuck this ";
$TESTS[2] = array("fuck this $om". "place$cm", "this place");
$RESULTS[2] = "fuck";
$TESTS[3] = array("fuck $om" . "this$cm $om". "place$cm", " place");
$RESULTS[3] = "fuck $om" . "this$cm";
$TESTS[4] = array("fuck this $om". "pl$cm" . "ace", "ace");
$RESULTS[4] = "fuck this $om" . "pl$cm";

foreach ($TESTS as $i => $in) {
	if (!array_key_exists($i, $RESULTS)) {
		echo "no expected result for $i\n";
		continue;
	}

	$res = debreach_wrap_rtrim($TESTS[$i][0], $TESTS[$i][1]);
	if ($res === $RESULTS[$i])
		echo "$i pass\n";
	else {
		echo "$i fail\n";
		echo "result:\n\"";
		print_r($res);
		echo "\"\nexpected:\n\"";
		print_r($RESULTS[$i]);
		echo "\"\n";
	}
}
?>
