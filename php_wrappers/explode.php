<?php
$open_marker = "DBXX";
$close_marker = "XXBD";

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
	print_r($positions);
	for ($i = 0; $i < count($positions); $i++) {
		$index_in_part = $positions[$i] - $part_offset + $marker_offset;
		if ($index_in_part < strlen($parts[$part_i])) {
			// this marker belongs in this part
			if ($open) {
				$parts[$part_i] = substr_replace($parts[$part_i], $open_marker, $index_in_part, 0);
				$marker_offset += strlen($open_marker);
				$open = false;
			}
			else {
				$parts[$part_i] = substr_replace($parts[$part_i], $close_marker, $index_in_part, 0);
				$marker_offset += strlen($close_marker);
				$open = true;
			}
		} else {
			$part_offset += strlen($parts[$part_i]) + strlen($delim) - $marker_offset;
			$part_i++;
			$marker_offset = 0;
			$index_in_part = $positions[$i] - $part_offset;
			while ($index_in_part >= strlen($parts[$part_i])) {
				$part_offset += strlen($parts[$part_i]) + strlen($delim);
				$part_i++;
				$index_in_part = $positions[$i] - $part_offset;
			}

			$index_in_part = max($index_in_part, 0);

			if ($open) {
				echo "else open: $index_in_part, " . strlen($parts[$part_i]) . "\n";
				$parts[$part_i] = substr_replace($parts[$part_i], $open_marker, $index_in_part, 0);
				$marker_offset += strlen($open_marker);
				$open = false;
			}
			else {
				echo "else close: $index_in_part, " . strlen($parts[$part_i]) . "\n";
				$parts[$part_i] = substr_replace($parts[$part_i], $close_marker, $index_in_part, 0);
				$marker_offset += strlen($close_marker);
				$open = true;
			}
		}
	}
	return $parts;
}

$input_string = "yo 12" . $open_marker . "3 hey 123 world 1" . $close_marker . "23 brandon " . $open_marker . " here " . $close_marker;

//$input_string = "one" . $open_marker . "hey" . $close_marker . $open_marker . "two" . $close_marker;

print_r(debreach_wrap_explode2("123", $input_string));

?>
