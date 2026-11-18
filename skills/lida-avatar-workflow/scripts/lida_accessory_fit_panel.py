# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Lida
"""Optional Blender sidebar panel for lida_accessory_fit.py (session use; nothing is installed).

Start Blender with ``--python THIS.py`` or run this file from the Text Editor. It registers a
"Lida Fit" tab in the 3D Viewport sidebar for the current session only and calls the functions of
lida_accessory_fit.py, which must sit in the same folder. The active object is the accessory;
the other selected meshes are the partners. Measure changes nothing. Fit adds a fitted copy and
hides the source in the viewport; undo works. The JSON report goes to the text block
"lida_accessory_fit_report". Nothing is saved to the blend file or to the preferences.
"""

import importlib.util
import json
from pathlib import Path

import bpy

bl_info = {
    "name": "Lida Accessory Fit Panel",
    "author": "Lida",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Lida Fit",
    "description": "Measure and fit a ring-like accessory to a body part by radial moves only",
    "category": "Object",
}
REPORT_TEXT = "lida_accessory_fit_report"


def _core():
    path = Path(__file__).resolve().with_name("lida_accessory_fit.py")
    if not path.is_file():
        raise RuntimeError("lida_accessory_fit.py must be in the same folder as this panel script")
    spec = importlib.util.spec_from_file_location("lida_accessory_fit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LidaAccessoryFitSettings(bpy.types.PropertyGroup):
    axis_mode: bpy.props.EnumProperty(name="Axis", items=[
        ("EXPLICIT", "Vector", "Use the axis vector below (most reliable)"),
        ("PARTNER", "Partner direction", "Longest direction of the partner near the accessory (arm, neck, waist)"),
        ("ACCESSORY", "Accessory flat direction", "Direction in which the accessory is thinnest"),
    ], default="EXPLICIT")
    axis: bpy.props.FloatVectorProperty(name="Axis vector", default=(0.0, 0.0, 1.0), subtype="DIRECTION")
    center_from_partner: bpy.props.BoolProperty(name="Center on partner", default=False)
    gap_mm: bpy.props.FloatProperty(name="Gap (mm)", default=1.2, min=0.0)
    band_axial: bpy.props.FloatProperty(name="Band share", default=1.0, min=0.05, max=1.0,
                                        description="Share of the axial extent that touches the partner; 1 = whole ring")
    band_high: bpy.props.BoolProperty(name="Band at the far end of the axis", default=False)
    push_only: bpy.props.BoolProperty(name="Push out only", default=False)
    rigid_islands_mm: bpy.props.FloatProperty(name="Rigid pieces up to (mm)", default=0.0, min=0.0)
    reach_mm: bpy.props.FloatProperty(name="Ray reach (mm)", default=40.0, min=1.0)
    summary: bpy.props.StringProperty(name="Last result")


def _arguments(context):
    settings = context.scene.lida_accessory_fit
    accessory = context.active_object
    partners = [obj for obj in context.selected_objects if obj is not accessory and obj.type == "MESH"]
    if accessory is None or accessory.type != "MESH" or not partners:
        raise ValueError("Select the partner meshes, then the accessory last (active)")
    options = {"gap_mm": settings.gap_mm, "band_axial": settings.band_axial,
               "band_side": "high" if settings.band_high else "low", "push_only": settings.push_only,
               "rigid_islands_mm": settings.rigid_islands_mm, "reach_mm": settings.reach_mm}
    keywords = {"options": options, "center_from": "partner" if settings.center_from_partner else "accessory"}
    if settings.axis_mode == "EXPLICIT":
        keywords["axis"] = tuple(settings.axis)
    else:
        keywords["axis_from"] = settings.axis_mode.lower()
    return accessory, partners, keywords


def _store(context, report):
    text = bpy.data.texts.get(REPORT_TEXT) or bpy.data.texts.new(REPORT_TEXT)
    text.clear()
    text.write(json.dumps(report, indent=2, ensure_ascii=False))
    part = report.get("after") or report["before"]
    gap = part["band_gap_mm"]
    context.scene.lida_accessory_fit.summary = "%s: band gap %.1f / %.1f / %.1f mm, inside %.1f%%, warnings %d" % (
        report["status"], gap["min"], gap["median"], gap["max"], part["all_points_inside_ratio"] * 100, len(report["warnings"]))


class LIDA_OT_accessory_measure(bpy.types.Operator):
    bl_idname = "lida.accessory_measure"
    bl_label = "Measure gap"
    bl_description = "Measure the gap between the active accessory and the other selected meshes; changes nothing"

    def execute(self, context):
        try:
            accessory, partners, keywords = _arguments(context)
            report = _core().measure(accessory, partners, **keywords)
        except Exception as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        _store(context, report)
        self.report({"WARNING"} if report["warnings"] else {"INFO"}, context.scene.lida_accessory_fit.summary)
        return {"FINISHED"}


class LIDA_OT_accessory_fit(bpy.types.Operator):
    bl_idname = "lida.accessory_fit"
    bl_label = "Fit a copy"
    bl_description = "Add a fitted copy of the active accessory; the source stays and is hidden in the viewport"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            accessory, partners, keywords = _arguments(context)
            copy, report = _core().fit_copy(accessory, partners, **keywords)
        except Exception as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        _store(context, report)
        if copy is None:
            self.report({"WARNING"}, "Refused: the placement does not match. See the report text block")
            return {"CANCELLED"}
        accessory.hide_set(True)
        self.report({"WARNING"} if report["warnings"] else {"INFO"}, context.scene.lida_accessory_fit.summary)
        return {"FINISHED"}


class LIDA_PT_accessory_fit(bpy.types.Panel):
    bl_idname = "LIDA_PT_accessory_fit"
    bl_label = "Accessory Fit"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Lida Fit"

    def draw(self, context):
        settings = context.scene.lida_accessory_fit
        layout = self.layout
        layout.label(text="Partners selected, accessory active")
        layout.prop(settings, "axis_mode")
        if settings.axis_mode == "EXPLICIT":
            layout.prop(settings, "axis", text="")
        layout.prop(settings, "center_from_partner")
        column = layout.column(align=True)
        column.prop(settings, "gap_mm")
        column.prop(settings, "band_axial")
        column.prop(settings, "band_high")
        column.prop(settings, "push_only")
        column.prop(settings, "rigid_islands_mm")
        column.prop(settings, "reach_mm")
        layout.operator(LIDA_OT_accessory_measure.bl_idname)
        layout.operator(LIDA_OT_accessory_fit.bl_idname)
        if settings.summary:
            layout.label(text=settings.summary)
            layout.label(text="Report: text block " + REPORT_TEXT)


CLASSES = (LidaAccessoryFitSettings, LIDA_OT_accessory_measure, LIDA_OT_accessory_fit, LIDA_PT_accessory_fit)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.lida_accessory_fit = bpy.props.PointerProperty(type=LidaAccessoryFitSettings)


def unregister():
    del bpy.types.Scene.lida_accessory_fit
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
