import FreeCADGui

class VPSolverOpenRadioss:
    def __init__(self, vobj):
        vobj.Proxy = self

    def setEdit(self, vobj, mode=0):
        from femtaskpanels.task_solver_openradioss import _TaskPanel
        panel = _TaskPanel(vobj.Object)
        FreeCADGui.Control.showDialog(panel)
        return True

    def doubleClicked(self, vobj):
        # Open the task panel for the solver
        self.setEdit(vobj, 0)
        return True

    def createMachine(self, obj, *args, **kwargs):
        # Placeholder for createMachine - implement based on original proxy
        pass
