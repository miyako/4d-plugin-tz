//%attributes = {}
//RFC to ISO conversion (specify format only)

$time:="Sun Sep 16 01:03:52 -0500 1973"
$fmt_in:="%a %b %d %T %z %Y"
$zone_out:=""
$fmt_out:="%FT%TZ"

$utc:=TZ Convert($time; $fmt_in; $zone_out; $fmt_out)
//1973-09-16T06:03:52.000Z

//RFC to ISO conversion in zone (specify format and zone)

$time:="Sun Sep 16 01:03:52 -0500 1973"
$fmt_in:="%a %b %d %T %z %Y"
$zone_out:="Australia/Sydney"
$fmt_out:="%FT%T %Z"

$aest:=TZ Convert($time; $fmt_in; $zone_out; $fmt_out)
//1973-09-16 16:03:52.000 AEST