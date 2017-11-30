<?php
$open_marker = "{{";
$close_marker = "}}";

function debreach_wrap_explode2($delim, $string, $count = PHP_INT_MAX) {
	global $open_marker, $close_marker;

	// first get all of the regions that are tainted as byte ranges
	$open = true;
	$last_open = -1;
	$last_close = -1;
	$offset = 0;
	$positions = array();
	while (true) {
		if ($open) {
			$last_open = strpos($string, $open_marker, $last_open + 1);

			if ($last_open === false) break;
			elseif ($last_open < $last_close)
				throw new Exception("open marker appeared before last close marker");

			$positions[] = $last_open - $offset;
			$offset += strlen($open_marker);
			$open = false;
		} else {
			$last_close = strpos($string, $close_marker, $last_close + 1);
			
			if ($last_close === false)
				throw new Exception("unterminated open marker");
			elseif ($last_close < $last_open)
				throw new Exception("close marker appeared before open marker");

			$positions[] = $last_close - $offset;
			$offset += strlen($close_marker);
			$open = true;
		}
	}

	// do the exploding...
	$string = str_replace(array($open_marker, $close_marker), "", $string);
	$parts = explode($delim, $string, $count);

	// put the markers back in
	$part_i = 0; // the part we are working on
	$part_offset = 0; // the amount of string in the previously processed parts
	$marker_offset = 0; // the change in position due to adding in markers
	$open = true;
	for ($i = 0; $i < count($positions); $i += 2) {
		$open_i = $positions[$i] - $part_offset + $marker_offset;
		if ($open_i < strlen($parts[$part_i])) {
			// this marker belongs in this part
			$parts[$part_i] = substr_replace($parts[$part_i], $open_marker, $open_i, 0);
			$marker_offset += strlen($open_marker);
		} else {
			// move to the next part
			$part_offset += strlen($parts[$part_i]) + strlen($delim) - $marker_offset;
			$part_i++;
			$marker_offset = 0;
			$open_i = $positions[$i] - $part_offset;
			while ($open_i >= strlen($parts[$part_i])) {
				$part_offset += strlen($parts[$part_i]) + strlen($delim);
				$part_i++;
				$open_i = $positions[$i] - $part_offset;
			}

			$open_i = max($open_i, 0);

			$parts[$part_i] = substr_replace($parts[$part_i], $open_marker, $open_i, 0);
			$marker_offset += strlen($open_marker);
		}

		$close_i = $positions[$i + 1] - $part_offset + $marker_offset;
		if ($close_i <= strlen($parts[$part_i]) + strlen($delim)) {
			$parts[$part_i] = substr_replace($parts[$part_i], $close_marker, $close_i, 0);
			$marker_offset += strlen($close_marker);
		} else {
			$part_offset += strlen($parts[$part_i]) + strlen($delim) - $marker_offset;
			// close the open marker in this part
			$parts[$part_i] .= $close_marker;
			$part_i++;

			// open a new region
			$parts[$part_i] = $open_marker . $parts[$part_i];
			$marker_offset = strlen($open_marker);

			$close_i = $positions[$i + 1] - $part_offset + $marker_offset;
			while ($close_i > strlen($parts[$part_i]) + strlen($delim)) {
				$parts[$part_i] .= $close_marker;
				$part_offset += strlen($parts[$part_i]) + strlen($delim) - $marker_offset - strlen($close_marker);
				$part_i++;
				$parts[$part_i] = $open_marker . $parts[$part_i];
				$close_i = $positions[$i + 1] - $part_offset + $marker_offset;
			}

			$parts[$part_i] = substr_replace($parts[$part_i], $close_marker, $close_i, 0);
			$marker_offset += strlen($close_marker);
		}
	}
	return $parts;
}

$om = $open_marker;
$cm = $close_marker;
$TESTS = array();
$RESULTS = array();
// marker spans multiple regions
$TESTS[0] = $om . " yo 123 my 123 name 123 is " . $cm . " brandon";
$RESULTS[0] =  array("{{ yo }}", "{{ my }}", "{{ name }}", "{{ is }} brandon");
$TESTS[1] = "yo " . $om . "123 my 123 name 123 is " . $cm . " brandon";
$RESULTS[1] =  array("yo ", "{{ my }}", "{{ name }}", "{{ is }} brandon");
$TESTS[2] = "yo " . $om . "123 my 123 name 123 is brandon" . $cm;
$RESULTS[2] = array("yo ", "{{ my }}", "{{ name }}", "{{ is brandon}}");
$TESTS[3] = $om . " yo 123 my 123 name 123 is 12" . $cm . "3 brandon";
$RESULTS[3] = array("{{ yo }}", "{{ my }}", "{{ name }}", "{{ is }}", " brandon");
$TESTS[4] = "yo 1" . $om . "23 my 123 name 123 is " . $cm . " brandon";
$RESULTS[4] = array("yo ", "{{ my }}", "{{ name }}", "{{ is }} brandon");
$TESTS[5] = "yo 1" . $om . "23 my 123 name 123 is brandon123" . $cm;
$RESULTS[5] = array("yo ", "{{ my }}", "{{ name }}", "{{ is brandon}}", "");

// close marker is inside delim -- should appear at end of part
$TESTS[6] = "yo 123" . $om . " brandon 12" . $cm . "3 hey";
$RESULTS[6] = array("yo ", "{{ brandon }}", " hey");
$TESTS[7] = "yo 123" . $om . " brandon 12" . $cm . "3";
$RESULTS[7] = array("yo ", "{{ brandon }}", "");

// this should have an empty region in the last part
$TESTS[8] = "yo 123 brandon 12" . $om . "3" . $cm;
$RESULTS[8] = array("yo ", " brandon ", "$om$cm");

// make tests with multiple open markers in one part
$TESTS[9] = "safe 123 $om taint $cm safe $om taint $cm 123 safe";
$RESULTS[9] = array("safe ", " $om taint $cm safe $om taint $cm ", " safe");
$TESTS[10] = "safe $om 123 taint $cm safe $om taint $cm 123 safe";
$RESULTS[10] = array("safe $om $cm", "$om taint $cm safe $om taint $cm ", " safe");
$TESTS[11] = "safe 1$om" . "23 taint $cm safe $om taint $cm 123 safe";
$RESULTS[11] = array("safe ", "$om taint $cm safe $om taint $cm ", " safe");
$TESTS[12] = "safe 1$om" . "23 taint $cm safe $om taint 1$cm" . "23 safe";
$RESULTS[12] = array("safe ", "$om taint $cm safe $om taint $cm", " safe");
$TESTS[12] = "safe 1$om" . "23 taint $cm safe $om taint 123 sa$cm" . "fe";
$RESULTS[12] = array("safe ", "$om taint $cm safe $om taint $cm", "$om sa$cm" . "fe");
 
//$res = debreach_wrap_explode2("123", $TESTS[6]);
//print_r($res);
//exit(0);

foreach ($TESTS as $i => $in) {
	if (!array_key_exists($i, $RESULTS)) {
		echo "no expected result for $i\n";
		continue;
	}

	$res = debreach_wrap_explode2("123", $TESTS[$i]);
	if ($res === $RESULTS[$i])
		echo "$i pass\n";
	else {
		echo "$i fail\n";
		echo "result:\n";
		print_r($res);
		echo "expected:\n";
		print_r($RESULTS[$i]);
	}
}
?>
