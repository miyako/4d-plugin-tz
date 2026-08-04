# 4d-plugin-tz

The TZ plugin parses, reformats, and converts date/time strings between IANA time zones, and exposes the full IANA time zone database as JSON. It's built on Howard Hinnant's `date`/`tz` library (the reference implementation later folded into C++20 `<chrono>`), using the same `strftime`/`strptime`-style format tokens (`%F`, `%T`, `%z`, `%a`, etc.) for both parsing and output. Results come back as `Text`.

| Command | Returns | Purpose |
|---|---|---|
| [`TZ Convert`](#tz-convert) | Text | Parse a date/time string, optionally shift it and convert it into another time zone, and reformat it. |
| [`TZ Get zones`](#tz-get-zones) | Text | Return the full IANA time zone database as a JSON array, one entry per zone, evaluated for the current moment. |

**Platforms:** macOS and Windows (4D has no Linux runtime; there's no gap to work around here).

---

## Requirements & platform notes

- **Neither command ever raises a 4D error.** Every failure path — an unparseable `date_in`, an unrecognized `zone_out`, a malformed `format_out` token — resolves silently to a fallback or an empty string. Check the result value yourself; don't rely on error-trapping.
- **The time zone database must load successfully at plugin startup**, or zone-aware conversion silently stops working (see Error handling below for exactly how this can fail per platform).
- `TZ Convert`'s last parameter, `time_to_add`, is optional — it can be omitted entirely. This is demonstrated in the plugin's own sample code, not just inferred from the manifest (see that command's parameter table for the caveat on how confidently this is verified).
- `TZ Get zones` takes no parameters and returns a single JSON string; parse it with 4D's JSON-handling commands (e.g. `JSON Parse`) to work with it as a collection — check your Language Reference for the exact syntax on your 4D version, since it varies release to release.

---

## TZ Convert

### Syntax

```
TZ Convert ( date_in ; format_in ; zone_out ; format_out { ; time_to_add } ) → Text
```

| Parameter | Type | Description |
|---|---|---|
| `date_in` | Text | The date/time string to parse. |
| `format_in` | Text | A `strptime`-style format string describing `date_in`'s layout, e.g. `"%F %T %z"` or `"%a %b %d %T %z %Y"`. |
| `zone_out` | Text | IANA time zone name to convert into, e.g. `"Asia/Tehran"`. Pass an empty string (`""`) to skip zone conversion and just re-emit the parsed time in `format_out` as-is. |
| `format_out` | Text | A `strftime`-style format string for the result, e.g. `"%FT%TZ"` or `"%FT%T %Z"`. Pass an empty string to use the library's default representation (`YYYY-MM-DD HH:MM:SS.sss +offset` when zoned). |
| `time_to_add` | Longint | **Optional.** Seconds to add to `date_in` before conversion/formatting. In the shipped examples this comes from a 4D `Time` value coerced to a number (`$flight+0`). Can be omitted — the plugin's own sample file calls `TZ Convert` with only 4 arguments and gets the expected result. *(This is confirmed by observed sample usage, not by tracing the SDK's own parameter-defaulting code, which wasn't available for this review — worth a quick sanity check on your specific 4D version if this matters for a production build.)* |
| Result | Text | The converted/formatted date-time string, or an **empty string** if `date_in` couldn't be parsed against `format_in`. |

### Description

`time_to_add` is applied to the parsed time *before* any zone conversion happens. If `zone_out` is non-empty, the plugin attempts to build a zoned time in that zone; if that fails (an unrecognized zone name), it silently falls back to formatting the unzoned, adjusted time instead — you get a result either way, just not necessarily in the zone you asked for, and with no signal that the fallback happened.

If `format_out` is empty, you get the library's default stream representation, which includes millisecond precision and (when zoned) a numeric UTC offset suffix — see the `1978-12-31 12:01:00.000 -0500` style output in the examples below.

If `date_in` fails to parse against `format_in` at all, the command returns an empty string with no other indication of failure.

### Example

From the plugin's own test method (`Method2.4dm`) — duration arithmetic across a time zone change:

```4d
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
```

From the plugin's own test method (`Method3.4dm`) — RFC-to-ISO conversion, and the 4-argument call demonstrating `time_to_add` as optional:

```4d
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
```

A minimal variation, checking for the empty-string failure case:

```4d
$result:=TZ Convert("not a date"; "%F %T"; ""; "%FT%TZ")
If($result="")
    ALERT:C41("Could not parse the input date")
End if 
```

---

## TZ Get zones

### Syntax

```
TZ Get zones → Text
```

No parameters.

| Parameter | Type | Description |
|---|---|---|
| Result | Text | A JSON-encoded array (as `Text`) with one object per zone in the IANA time zone database. |

### Description

Each zone object has these properties, evaluated for the moment the command is called (not a static, zone-wide baseline):

| Property | Type | Description |
|---|---|---|
| `name` | String | IANA zone name, e.g. `"Asia/Tehran"`. |
| `abbrev` | String | The zone's current abbreviation at call time, e.g. `"CET"` or `"CEST"` depending on whether DST is active right now. |
| `local_time` | String | The current local wall-clock time in this zone. |
| `offset_time` | String | The current UTC offset, formatted as a duration (`%T` — `HH:MM:SS`). |
| `offset` | Integer | The same UTC offset, in **seconds**. |
| `save_time` | String | The current daylight-saving adjustment, formatted as a duration (`%T`). |
| `save` | Integer | The same daylight-saving adjustment, in **minutes** — a different unit from `offset`, don't assume they match. |
| `begin` | String | Start of the currently-active rule (offset/abbreviation) for this zone. |
| `end` | String | End of the currently-active rule for this zone. |

Because `abbrev`, `offset`, `save`, `begin`, and `end` are all evaluated against "now," calling this command at different times of year can return different values for the same zone (e.g. a zone's `offset` and `abbrev` will differ between its standard-time and daylight-saving periods). For zones with no active transition rule, `begin`/`end` can carry very large or very early sentinel date/time values rather than a normal-looking date — this wasn't independently verified against every zone in the database, so treat an implausible `begin`/`end` value as expected rather than a bug.

### Example

From the plugin's own test method (`Method1.4dm`):

```4d
//%attributes = {}
$zones:=TZ Get zones

ALERT:C41($zones)
```

Parsing the result into something you can iterate (exact JSON-parsing syntax depends on your 4D version — check your Language Reference):

```4d
$json:=TZ Get zones
$zones:=JSON Parse($json)  //check exact syntax/behavior on your 4D version

For each($zone; $zones)
    If($zone.name="Europe/London")
        ALERT:C41($zone.abbrev+" "+String:C10($zone.offset)+"s")
    End if 
End for each 
```

---

## Error handling & troubleshooting

- **Neither command raises a 4D error, ever.** Both fail silently — check the returned `Text` value yourself (empty string for `TZ Convert`, or inspect the parsed zone list for `TZ Get zones`).
- **`TZ Convert` returns an empty string if `date_in` doesn't match `format_in`.** There's no other signal; a mismatched format token, wrong literal text, or garbage input all produce the same empty result.
- **An unrecognized `zone_out` value doesn't fail loudly — it silently falls back to unzoned output.** You'll still get a result string, just not converted into the zone you asked for, so a typo'd zone name (e.g. `"Asia/Tehren"`) won't be obvious from the output alone.
- **A malformed `format_out` token is now handled the same way — falls back silently rather than freezing.** This relies on the exception-safety fixes applied to `4DPlugin.cpp` during code review (the previously-unprotected `format()` call in the no-zone fallback path). If you're running a build from before that fix, a bad `format_out` string could instead hang the command indefinitely, since the manifest declares a return type and 4D would be left waiting on a value that never arrives.
- **Time zone data has to load at startup, or zone conversion quietly stops working.** On macOS, this depends on the plugin bundle being found by its bundle identifier and containing a `tzdata` resource; on Windows, it depends on the plugin's binary being found under its expected module name and a `Resources\tzdata\` folder existing one directory level up from it. If either lookup fails, no error is surfaced — `zone_out`-bearing `TZ Convert` calls will simply behave as if the zone conversion failed (see above), and any zone-info fields returned by `TZ Get zones` will reflect whatever partial/absent data is available.
- **`offset` is in seconds; `save` is in minutes.** Easy to assume these share a unit since they're both integers describing a time shift — they don't.

---

## Quick reference

```4d
// Parse, shift by a Time value's worth of seconds, and convert zones
$result:=TZ Convert($date_string; "%F %T %z"; "Asia/Tehran"; "%FT%T %Z"; $time_value+0)

// Same, with no zone conversion, no extra shift, default output formatting
$result:=TZ Convert($date_string; "%F %T %z"; ""; "")

// Full zone database as JSON
$zones_json:=TZ Get zones
```

