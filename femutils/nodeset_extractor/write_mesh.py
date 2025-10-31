# ***************************************************************************
# *   Copyright (c) 2021 Bernd Hahnebach <bernd@bimstatik.org>              *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

__title__ = "FreeCAD FEM calculix write inpfile mesh"
__author__ = "Bernd Hahnebach"
__url__ = "https://www.freecad.org"


import codecs
from os.path import join

from femmesh import meshtools


def write_mesh(ORwriter):

    element_param = 1  # highest element order only
    group_param = False  # do not write mesh group data

    # Use reduced integration beam elements if this option is enabled in ccx solver settings
    vol_variant = "standard"
    edge_variant = "beam"
    if ORwriter.solver_obj.BeamReducedIntegration:
        edge_variant = "beam reduced"
    # Check to see if fluid sections are in analysis and use D network element type
    if ORwriter.member.geos_fluidsection:
        edge_variant = "network"

    # Use 2D elements if model space is not set to 3D
    if ORwriter.solver_obj.ModelSpace == "3D":
        face_variant = "shell"
    elif ORwriter.solver_obj.ModelSpace == "plane stress":
        face_variant = "stress"
    elif ORwriter.solver_obj.ModelSpace == "plane strain":
        face_variant = "strain"
    elif ORwriter.solver_obj.ModelSpace == "axisymmetric":
        face_variant = "axisymmetric"

    if ORwriter.split_inpfile:
        write_name = "femesh"
        file_name_split = ORwriter.mesh_name + "_" + write_name + ".inp"
        ORwriter.femmesh_file = join(ORwriter.dir_name, file_name_split)

        ORwriter.femmesh.writeABAQUS(
            ORwriter.femmesh_file,
            element_param,
            group_param,
            volVariant=vol_variant,
            faceVariant=face_variant,
            edgeVariant=edge_variant,
        )

        inpfile = codecs.open(ORwriter.file_name, "w", encoding="utf-8")
        inpfile.write("{}\n".format(59 * "*"))
        inpfile.write(f"** {write_name}\n")
        inpfile.write(f"*INCLUDE,INPUT={file_name_split}\n")

    else:
        ORwriter.femmesh_file = ORwriter.file_name
        ORwriter.femmesh.writeABAQUS(
            ORwriter.femmesh_file,
            element_param,
            group_param,
            volVariant=vol_variant,
            faceVariant=face_variant,
            edgeVariant=edge_variant,
        )

        # reopen file with "append" to add all the rest
        inpfile = codecs.open(ORwriter.femmesh_file, "a", encoding="utf-8")
        inpfile.write("\n\n")

    return inpfile
