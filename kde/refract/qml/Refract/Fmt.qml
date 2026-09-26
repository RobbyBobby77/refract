pragma Singleton
import QtQuick

// Number formatting in the style of macOS: decimal units by default,
// "—" for unknown values, tabular-friendly output.
QtObject {
    readonly property string dash: "—"

    function isNum(v) { return v !== undefined && v !== null && !isNaN(v) }

    function num(v, digits) {
        if (!isNum(v)) return dash
        return Number(v).toLocaleString(Qt.locale(), "f", digits === undefined ? 0 : digits)
    }

    function percent(v, digits) {
        if (!isNum(v)) return dash
        return num(v, digits === undefined ? 0 : digits) + "%"
    }

    function _scaled(value, base, units, digitsHint) {
        let i = 0
        let v = Math.abs(value)
        while (v >= base && i < units.length - 1) { v /= base; ++i }
        const digits = digitsHint !== undefined ? digitsHint : (i === 0 ? 0 : (v < 10 ? 2 : v < 100 ? 1 : 0))
        return (value < 0 ? "-" : "") + num(v, i === 0 ? 0 : digits) + " " + units[i]
    }

    function bytes(v, digits) {
        if (!isNum(v)) return dash
        if (v === 0) return "Zero KB"          // as Activity Monitor says it
        return Prefs.decimalUnits
            ? _scaled(v, 1000, ["bytes", "KB", "MB", "GB", "TB", "PB"], digits)
            : _scaled(v, 1024, ["bytes", "KiB", "MiB", "GiB", "TiB", "PiB"], digits)
    }

    function rate(v, digits) {
        if (!isNum(v)) return dash
        return Prefs.decimalUnits
            ? _scaled(v, 1000, ["B/s", "KB/s", "MB/s", "GB/s", "TB/s"], digits)
            : _scaled(v, 1024, ["B/s", "KiB/s", "MiB/s", "GiB/s", "TiB/s"], digits)
    }

    function netRate(v, digits) {
        if (!isNum(v)) return dash
        if (!Prefs.networkBits) return rate(v, digits)
        return _scaled(v * 8, 1000, ["bps", "Kbps", "Mbps", "Gbps", "Tbps"], digits)
    }

    function freq(mhz) {
        if (!isNum(mhz) || mhz <= 0) return dash
        return mhz >= 1000 ? num(mhz / 1000, 2) + " GHz" : num(mhz, 0) + " MHz"
    }

    function temp(c) {
        if (!isNum(c)) return dash
        return Prefs.fahrenheit ? num(c * 9 / 5 + 32, 0) + " °F" : num(c, 0) + " °C"
    }

    function watts(w) {
        if (!isNum(w)) return dash
        return num(w, w < 10 ? 1 : 0) + " W"
    }

    function rpm(v) {
        if (!isNum(v)) return dash
        return num(v, 0) + " RPM"
    }

    function duration(s) {
        if (!isNum(s)) return dash
        s = Math.floor(s)
        const d = Math.floor(s / 86400)
        const h = Math.floor((s % 86400) / 3600)
        const m = Math.floor((s % 3600) / 60)
        const sec = s % 60
        const pad = x => (x < 10 ? "0" : "") + x
        return (d > 0 ? d + "d " : "") + pad(h) + ":" + pad(m) + ":" + pad(sec)
    }

    function shortDuration(s) {
        if (!isNum(s) || s <= 0) return dash
        const h = Math.floor(s / 3600)
        const m = Math.round((s % 3600) / 60)
        return h > 0 ? h + " hr " + m + " min" : m + " min"
    }

    function dateTime(epoch) {
        if (!isNum(epoch) || epoch <= 0) return dash
        return new Date(epoch * 1000).toLocaleString(Qt.locale(), Locale.ShortFormat)
    }

    // A "nice" ceiling for autoscaled graphs: 1, 2, 5 × 10^n.
    function niceMax(v) {
        if (!isNum(v) || v <= 0) return 1
        const exp = Math.pow(10, Math.floor(Math.log10(v)))
        const f = v / exp
        return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * exp
    }
}
