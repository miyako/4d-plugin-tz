//%attributes = {}
//duration over time zone change 

$departure:="1978-12-30 12:01:00 -0500"
$fmt_in:="%F %T %z"
$fmt_out:="%F %T %z"
$zone_out:="Asia/Tehran"
$flight:=?14:44:00?

$arrival:=TZ Convert($departure; \
$fmt_in; \
$zone_out; \
$fmt_out; \
$flight+0)
//1978-12-31 11:45:00.000 +0400

//day later...
$departure:=TZ Convert($departure; \
$fmt_in; \
"America/New_York"; \
$fmt_out; \
?24:00:00?+0)
//1978-12-31 12:01:00.000 -0500

$arrival:=TZ Convert($departure; \
$fmt_in; \
$zone_out; \
$fmt_out; \
$flight+0)
//1979-01-01 11:15:00.000 +0330

