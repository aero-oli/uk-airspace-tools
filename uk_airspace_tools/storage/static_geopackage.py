from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ..providers.nats_aip_dataset import PermanentAirspaceFeature
from .static_schema import STATIC_ATTR_FIELDS, STATIC_CATEGORY_TO_LAYER, STATIC_LAYER_NAMES


class StaticAirspaceCache:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def write(self, features: list[PermanentAirspaceFeature], metadata: dict | None = None) -> Path:
        try:
            from osgeo import gdal, ogr, osr
        except ImportError as exc:
            raise RuntimeError("GDAL/OGR is required to write the permanent airspace cache.") from exc

        gdal.UseExceptions()
        ogr.UseExceptions()

        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                self.path.unlink()
            except OSError as exc:
                raise RuntimeError(f"Could not replace existing GeoPackage at {self.path}. Close any QGIS layers using it and try again.") from exc

        driver = ogr.GetDriverByName("GPKG")
        datasource = driver.CreateDataSource(str(self.path))
        if datasource is None:
            raise RuntimeError(f"Could not create GeoPackage at {self.path}")

        spatial_ref = osr.SpatialReference()
        spatial_ref.ImportFromEPSG(4326)

        layers = {}
        for key, layer_name in STATIC_LAYER_NAMES.items():
            if key in {"metadata", "warnings"}:
                continue
            layers[key] = self._create_feature_layer(datasource, layer_name, spatial_ref)
        warning_layer = self._create_warning_layer(datasource)
        metadata_layer = self._create_metadata_layer(datasource)

        for feature in features:
            target_key = STATIC_CATEGORY_TO_LAYER.get(feature.category, "other")
            self._write_feature(ogr, layers[target_key], feature)
            for warning in feature.parse_warnings:
                self._write_warning(warning_layer, feature.id, warning)

        metadata = dict(metadata or {})
        metadata.setdefault("refreshed_at", datetime.now(timezone.utc).isoformat())
        metadata.setdefault("feature_count", str(len(features)))
        for key, value in metadata.items():
            self._write_metadata(metadata_layer, key, "" if value is None else str(value))

        datasource.FlushCache()
        datasource = None
        return self.path

    def _create_feature_layer(self, datasource, name, spatial_ref):
        from osgeo import ogr

        layer = datasource.CreateLayer(name, spatial_ref, ogr.wkbPolygon)
        for field_name in STATIC_ATTR_FIELDS:
            if field_name.endswith("_value") or field_name in {"lower_altitude_ft", "upper_altitude_ft"}:
                field = ogr.FieldDefn(field_name, ogr.OFTReal)
            elif field_name == "parse_warning_count":
                field = ogr.FieldDefn(field_name, ogr.OFTInteger)
            else:
                field = ogr.FieldDefn(field_name, ogr.OFTString)
                field.SetWidth(0)
            layer.CreateField(field)
        return layer

    def _write_feature(self, ogr, layer, feature: PermanentAirspaceFeature) -> None:
        ogr_feature = ogr.Feature(layer.GetLayerDefn())
        for field_name in STATIC_ATTR_FIELDS:
            value = self._attribute_value(feature, field_name)
            if value is not None:
                ogr_feature.SetField(field_name, value)

        if feature.geometry_wkt:
            geometry = ogr.CreateGeometryFromWkt(feature.geometry_wkt)
            if geometry is not None:
                ogr_feature.SetGeometry(geometry)
        layer.CreateFeature(ogr_feature)
        ogr_feature = None

    @staticmethod
    def _attribute_value(feature: PermanentAirspaceFeature, field_name: str):
        if field_name == "parse_warning_count":
            return len(feature.parse_warnings)
        value = getattr(feature, field_name)
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def _create_warning_layer(self, datasource):
        from osgeo import ogr

        layer = datasource.CreateLayer(STATIC_LAYER_NAMES["warnings"], None, ogr.wkbNone)
        layer.CreateField(ogr.FieldDefn("feature_id", ogr.OFTString))
        field = ogr.FieldDefn("warning", ogr.OFTString)
        field.SetWidth(0)
        layer.CreateField(field)
        return layer

    def _create_metadata_layer(self, datasource):
        from osgeo import ogr

        layer = datasource.CreateLayer(STATIC_LAYER_NAMES["metadata"], None, ogr.wkbNone)
        layer.CreateField(ogr.FieldDefn("key", ogr.OFTString))
        field = ogr.FieldDefn("value", ogr.OFTString)
        field.SetWidth(0)
        layer.CreateField(field)
        return layer

    @staticmethod
    def _write_warning(layer, feature_id: str, warning: str) -> None:
        from osgeo import ogr

        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("feature_id", feature_id)
        feature.SetField("warning", warning)
        layer.CreateFeature(feature)
        feature = None

    @staticmethod
    def _write_metadata(layer, key: str, value: str) -> None:
        from osgeo import ogr

        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetField("key", key)
        feature.SetField("value", value)
        layer.CreateFeature(feature)
        feature = None
