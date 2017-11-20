# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#  ***** BEGIN GPL LICENSE BLOCK *****
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  The Original Code is Copyright (C) 2012 by Philip Lafleur.
#  All rights reserved.
#
#  Contact:      bksnzq {at} gmail {dot} com
#
#  The Original Code is: all of this file.
#
#  Contributor(s): none yet.
#
#  ***** END GPL LICENSE BLOCK *****

bl_info = {
    "name": "Remirror",
    "author": "Philip Lafleur",
    "version": (0, 9),
    "blender": (2, 6, 3),
    "location": "View3D > Object > Mirror > Remirror",
    "description": "Non-destructively update symmetry of a mirrored mesh",
    "warning": "",
    "wiki_url": ("http://wiki.blender.org/index.php/Extensions:2.6"
                 "/Py/Scripts/Mesh/Remirror"),
    "tracker_url": ("http://projects.blender.org/tracker/index.php?"
                    "func=detail&aid=32166&group_id=153&atid=467"),
    "category": "Mesh"}

import bpy
import bmesh

ERR_ASYMMETRY    = "Asymmetry encountered (central edge loop(s) not centered?)"
ERR_BAD_PATH     = "Couldn't follow edge path (inconsistent normals?)"
ERR_CENTRAL_LOOP = "Failed to find central edge loop(s). Please recenter."
ERR_FACE_COUNT   = "Encountered edge with more than 2 faces attached."

CENTRAL_LOOP_MARGIN = 1e-5

class Remirror (bpy.types.Operator):
    bl_idname      = "mesh.remirror"
    bl_label       = "Remirror"
    bl_description = "Non-destructively update symmetry of a mirrored mesh"
    bl_options     = {'REGISTER', 'UNDO'}

    axis   = bpy.props.EnumProperty (
                 name = "Axis",
                 description = "Mirror axis",
                 items = (('X', "X", "X Axis"),
                          ('Y', "Y", "Y Axis"),
                          ('Z', "Z", "Z Axis")))
    source = bpy.props.EnumProperty (
                 name = "Source",
                 description = "Half of mesh to be mirrored on the other half",
                 items = (('POSITIVE', "Positive side", "Positive side"),
                          ('NEGATIVE', "Negative side", "Negative side")))

    @classmethod
    def poll (cls, context):
        obj = context.active_object
        return (obj and obj.type == 'MESH' and context.mode == 'OBJECT')

    def execute (self, context):
        mesh = bpy.context.active_object.data

        try:
            remirror (mesh, {'X': 0, 'Y': 1, 'Z': 2}[self.axis], self.source)
        except ValueError as e:
            self.report ({'ERROR'}, str (e))

        return {'FINISHED'}


def nextEdgeCCW (v, e_prev):
    """
    Return the edge following e_prev in counter-clockwise order around vertex v
    by following the winding of the surrounding faces.
    """
    if len (e_prev.link_loops) == 2:
        # Assumes continuous normals
        if e_prev.link_loops[0].vert is v:
            return e_prev.link_loops[0].link_loop_prev.edge
        return e_prev.link_loops[1].link_loop_prev.edge

    elif len (e_prev.link_loops) == 1:
        # Assumes only two single-loop edges per vertex
        if e_prev.link_loops[0].vert is v:
            return e_prev.link_loops[0].link_loop_prev.edge
        for edge in v.link_edges:
            if len (edge.link_loops) == 1 and edge is not e_prev:
                return edge

    else:
        raise ValueError (ERR_FACE_COUNT)

def nextEdgeCW (v, e_prev):
    """
    Return the edge following e_prev in clockwise order around vertex v
    by following the winding of the surrounding faces.
    """
    if len (e_prev.link_loops) == 2:
        # Assumes continuous normals
        if e_prev.link_loops[0].vert is not v:
            return e_prev.link_loops[0].link_loop_next.edge
        return e_prev.link_loops[1].link_loop_next.edge

    elif len (e_prev.link_loops) == 1:
        # Assumes only two single-loop edges per vertex
        if e_prev.link_loops[0].vert is not v:
            return e_prev.link_loops[0].link_loop_next.edge
        for edge in v.link_edges:
            if len (edge.link_loops) == 1 and edge is not e_prev:
                return edge

    else:
        raise ValueError (ERR_FACE_COUNT)


def visitMirrorVerts (v_start, e_start, visitor):
    """
    Call visitor(v_right, v_left) for each pair of mirrored vertices that
    are reachable by following a path from v_start along connected edges
    without intersecting the central edge loop(s) or any previously-visited
    vertices.

    v_start: a vertex on a central edge loop
    e_start: an edge on a central edge loop such that the next edge in
             counter-clockwise order around v_start is on the positive side
             of the central loop
    """
    er = e_start
    el = e_start
    vr = v_start
    vl = v_start
    path = [(er, el)]

    while path:
        er = nextEdgeCCW (vr, er)
        el = nextEdgeCW (vl, el)

        if er is path[-1][0] or er.tag:
            if not (el is path[-1][1] or el.tag):
                raise ValueError (ERR_ASYMMETRY)
            er = path[-1][0]
            el = path[-1][1]
            vr = er.other_vert (vr)
            vl = el.other_vert (vl)
            path.pop ()
            continue

        if el is path[-1][1] or el.tag:
            raise ValueError (ERR_ASYMMETRY)

        vr = er.other_vert (vr)
        vl = el.other_vert (vl)

        if vr is None:
            raise ValueError (ERR_BAD_PATH)
        if vr.tag:
            if vl is None or not vl.tag:
                raise ValueError (ERR_ASYMMETRY)
            vr = er.other_vert (vr)
            vl = el.other_vert (vl)
            continue

        if vl is None or vl.tag:
            raise ValueError (ERR_ASYMMETRY)

        path.append ((er, el))
        visitor (vr, vl)
        vr.tag = True
        vl.tag = True

def updateVerts (v_start, e_start, axis, source):
    def updatePositive (v_right, v_left):
        v_left.co = v_right.co
        v_left.co[axis] = -v_right.co[axis]

    def updateNegative (v_right, v_left):
        v_right.co = v_left.co
        v_right.co[axis] = -v_left.co[axis]

    visitMirrorVerts (
        v_start, e_start,
        updatePositive if source == 'POSITIVE' else updateNegative)


def tagCentralEdgePath (v, e):
    """
    Tag each edge along the path starting at edge e in the direction of vertex v
    such that the path evenly divides the number of edges connected to each
    vertex.
    """
    while True:
        e.tag = True

        if len (v.link_edges) % 2:
            if len (v.link_faces) == len (v.link_edges):
                raise ValueError (ERR_CENTRAL_LOOP)
            else:
                return

        for i in range (len (v.link_edges) // 2):
            e = nextEdgeCCW (v, e)

        v = e.other_vert (v)
        if v is None:
            raise ValueError (ERR_BAD_PATH)

        if e.tag:
            return

def tagCentralLoops (bm, axis):
    """
    Attempt to find and tag the edges on the central loop(s) of the bmesh bm
    aligned with the given axis.
    """
    for v in bm.verts:
        v.tag = False
    for e in bm.edges:
        e.tag = False

    verts = []
    edges = []

    for v in bm.verts:
        if (v.co[axis] < CENTRAL_LOOP_MARGIN
                and v.co[axis] > -CENTRAL_LOOP_MARGIN):
            v.tag = True
            verts.append (v)

    for v in verts:
        for e in v.link_edges:
            if e.other_vert (v).tag:
                e.tag = True
                edges.append (e)

    for v in verts:
        v.tag = False

    if not (edges and verts):
        raise ValueError (ERR_CENTRAL_LOOP)

    for e in edges:
        tagCentralEdgePath (e.verts[0], e)
        tagCentralEdgePath (e.verts[1], e)


def startingVertex (edge, axis):
    """
    Return the endpoint of the given edge such that the next edge in
    counter-clockwise order around the endpoint is on the positive side of
    the given axis.
    """
    if len (edge.link_loops) != 2:
        raise ValueError (ERR_FACE_COUNT)

    loops = sorted (edge.link_loops,
                    key = lambda loop: loop.face.calc_center_median ()[axis])

    return loops[-1].vert

def remirror (mesh, axis, source):
    bm = bmesh.new ()
    bm.from_mesh (mesh)

    tagCentralLoops (bm, axis)

    for e in bm.edges:
        if e.tag:
            e.verts[0].co[axis] = 0.
            e.verts[1].co[axis] = 0.
            e.verts[0].tag = True
            e.verts[1].tag = True

    for e in bm.edges:
        if e.tag:
            updateVerts (startingVertex (e, axis), e, axis, source)

    for v in bm.verts:
        v.tag = False
    for e in bm.edges:
        e.tag = False

    bm.to_mesh (mesh)
    mesh.update (calc_tessface = True)


def menuFunc (self, context):
    self.layout.operator (Remirror.bl_idname)

def register ():
    bpy.utils.register_class (Remirror)
    bpy.types.VIEW3D_MT_mirror.append (menuFunc)

def unregister ():
    bpy.types.VIEW3D_MT_mirror.remove (menuFunc)
    bpy.utils.unregister_class (Remirror)


if __name__ == "__main__":
    register ()
