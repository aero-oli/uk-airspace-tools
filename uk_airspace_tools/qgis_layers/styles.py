def apply_notam_style(layer, geometry_kind: str) -> None:
    try:
        from qgis.core import (
            QgsFillSymbol,
            QgsMarkerSymbol,
            QgsRuleBasedRenderer,
            QgsSingleSymbolRenderer,
        )
        from qgis.PyQt.QtGui import QColor
    except ImportError:
        return

    if geometry_kind == "polygon":
        root = QgsRuleBasedRenderer.Rule(None)
        rules = [
            ("Obstacles", "\"activity_group\" = 'Obstacles' AND (\"radius_nm\" IS NULL OR \"radius_nm\" <= 100)", QColor(198, 118, 0), QColor(198, 118, 0, 22), "solid"),
            ("Aerial activity", "\"activity_group\" = 'Aerial activity' AND (\"radius_nm\" IS NULL OR \"radius_nm\" <= 100)", QColor(205, 46, 46), QColor(205, 46, 46, 22), "solid"),
            ("Airspace restrictions", "\"activity_group\" = 'Airspace restrictions' AND (\"radius_nm\" IS NULL OR \"radius_nm\" <= 100)", QColor(126, 67, 176), QColor(126, 67, 176, 20), "solid"),
            ("Aerodrome and runway", "\"activity_group\" = 'Aerodrome and runway' AND (\"radius_nm\" IS NULL OR \"radius_nm\" <= 100)", QColor(28, 130, 142), QColor(28, 130, 142, 20), "solid"),
            ("Navigation and procedures", "\"activity_group\" = 'Navigation and procedures' AND (\"radius_nm\" IS NULL OR \"radius_nm\" <= 100)", QColor(45, 99, 180), QColor(45, 99, 180, 18), "solid"),
            ("Other local/regional", "(\"activity_group\" IS NULL OR \"activity_group\" = 'Other') AND (\"radius_nm\" IS NULL OR \"radius_nm\" <= 100)", QColor(95, 95, 95), QColor(95, 95, 95, 16), "solid"),
            ("Large area (>100 NM)", "\"radius_nm\" > 100", QColor(70, 70, 70), QColor(70, 70, 70, 6), "dash"),
            ("Cancelled/expired", "\"status\" IN ('cancelled', 'expired')", QColor(120, 120, 120), QColor(120, 120, 120, 8), "dot"),
        ]
        for label, expression, outline, fill, outline_style in rules:
            symbol = QgsFillSymbol.createSimple(
                {
                    "color": fill.name(QColor.HexArgb),
                    "outline_color": outline.name(QColor.HexArgb),
                    "outline_width": "0.35",
                    "outline_style": outline_style,
                }
            )
            rule = QgsRuleBasedRenderer.Rule(symbol, 0, 0, expression, label)
            root.appendChild(rule)
        layer.setRenderer(QgsRuleBasedRenderer(root))
    elif geometry_kind == "point":
        symbol = QgsMarkerSymbol.createSimple(
            {
                "name": "circle",
                "color": "220,30,30,160",
                "outline_color": "60,60,60",
                "size": "3.0",
            }
        )
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))


def apply_static_airspace_style(layer, category: str) -> None:
    try:
        from qgis.core import QgsFillSymbol, QgsSingleSymbolRenderer
        from qgis.PyQt.QtGui import QColor
    except ImportError:
        return

    palette = {
        "Controlled airspace": (QColor(31, 96, 180), QColor(31, 96, 180, 18), "solid"),
        "Aerodrome zones": (QColor(0, 125, 135), QColor(0, 125, 135, 20), "solid"),
        "Airspace restrictions": (QColor(160, 35, 80), QColor(160, 35, 80, 22), "dash"),
        "Radio/transponder zones": (QColor(115, 80, 170), QColor(115, 80, 170, 14), "dash"),
        "Airways/routes": (QColor(80, 80, 80), QColor(80, 80, 80, 8), "dot"),
        "Other permanent airspace": (QColor(95, 95, 95), QColor(95, 95, 95, 10), "solid"),
    }
    outline, fill, style = palette.get(category, palette["Other permanent airspace"])
    symbol = QgsFillSymbol.createSimple(
        {
            "color": fill.name(QColor.HexArgb),
            "outline_color": outline.name(QColor.HexArgb),
            "outline_width": "0.35",
            "outline_style": style,
        }
    )
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))


def apply_map_tip(layer) -> None:
    template = """
    <b>[% "id" %]</b><br/>
    Status: [% "status" %]<br/>
    Type: [% "activity_group" %]<br/>
    Effective: [% "effective_start" %] to [% "effective_end" %]<br/>
    Radius: [% "radius_nm" %] NM<br/>
    Limits: [% "lower_limit_raw" %] / [% "upper_limit_raw" %]<br/>
    Q-code: [% "qcode" %]<br/>
    Warnings: [% "parse_warning_count" %]<br/>
    <pre>[% "raw_text" %]</pre>
    """
    try:
        layer.setMapTipTemplate(template)
    except AttributeError:
        pass
