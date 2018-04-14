<?php
$open_marker = "{{";
$close_marker = "}}";
function debreach_wrap_strlen($string) {
	global $open_marker, $close_marker;
	return strlen($string) - substr_count($string, $open_marker)*strlen($open_marker) - substr_count($string, $close_marker)*strlen($close_marker);
}	

$TESTS = array();
$RESULTS = array();

$om = $open_marker;
$cm = $close_marker;
$TESTS[0] = "sldfjlk $om lsdjfds $cm lkjsdflsdj $om sjdksd $cm";
$RESULTS[0] = strlen("sldfjlk  lsdjfds  lkjsdflsdj  sjdksd ");

echo debreach_wrap_strlen($TESTS[0]) . "\n";
echo $RESULTS[0] . "\n";
?>
