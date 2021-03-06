#!/usr/bin/env python
"""
Helper class for generating LEMS xml files for simulations
"""
    
import airspeed
import os.path

from pyneuroml import __version__
from pyneuroml.pynml import read_neuroml2_file
from pyneuroml.pynml import read_lems_file

class LEMSSimulation():
    
    TEMPLATE_FILE = "%s/LEMS_TEMPLATE.xml"%(os.path.dirname(__file__))
    
    lems_info = {}
    
    
    def __init__(self, sim_id, duration, dt, target=None, comment="\n\n        This LEMS file has been automatically generated using PyNeuroML v%s\n\n    "%__version__):
        self.lems_info['sim_id'] = sim_id
        self.lems_info['duration'] = duration
        self.lems_info['dt'] = dt
        self.lems_info['comment'] = comment
        
        self.lems_info['include_files'] = []
        self.lems_info['displays'] = []
        self.lems_info['output_files'] = []
        
        if target:
            self.lems_info['target'] = target
        
        
    def assign_simulation_target(self, target):
        self.lems_info['target'] = target
        
        
    def include_neuroml2_file(self, nml2_file_name, include_included=True):
        self.lems_info['include_files'].append(nml2_file_name)
        if include_included:
            cell = read_neuroml2_file(nml2_file_name)
            for include in cell.includes:
                self.lems_info['include_files'].append(include.href)
        
        
    def include_lems_file(self, lems_file_name, include_included=True):
        self.lems_info['include_files'].append(lems_file_name)
        if include_included:
            model = read_lems_file(lems_file_name)
            for inc in model.included_files:
                self.lems_info['include_files'].append(inc)
        
        
    def create_display(self, id, title, ymin, ymax, timeScale="1ms"):
        disp = {}
        self.lems_info['displays'].append(disp)
        disp['id'] = id
        disp['title'] = title
        disp['ymin'] = ymin
        disp['ymax'] = ymax
        disp['time_scale'] = timeScale
        disp['lines'] = []
        
        
    def create_output_file(self, id, file_name):
        of = {}
        self.lems_info['output_files'].append(of)
        of['id'] = id
        of['file_name'] = file_name
        of['columns'] = []
        
        
    def add_line_to_display(self, display_id, line_id, quantity, scale, color, timeScale="1ms"):
        disp = None
        for d in self.lems_info['displays']:
            if d['id'] == display_id:
                disp = d
                
        line = {}
        disp['lines'].append(line)
        line['id'] = line_id
        line['quantity'] = quantity
        line['scale'] = scale
        line['color'] = color
        line['time_scale'] = timeScale
        
        
    def add_column_to_output_file(self, output_file_id, column_id, quantity):
        of = None
        for o in self.lems_info['output_files']:
            if o['id'] == output_file_id:
                of = o
                
        column = {}
        of['columns'].append(column)
        column['id'] = column_id
        column['quantity'] = quantity
        
    
    def to_xml(self):
        templfile = self.TEMPLATE_FILE
        if not os.path.isfile(templfile):
            templfile = '.' + templfile
        with open(templfile) as f:
            templ = airspeed.Template(f.read())
        return templ.merge(self.lems_info)
    

    def save_to_file(self, file_name=None):
        if file_name==None:
            file_name = "LEMS_%s.xml"%self.lems_info['sim_id']
            
        lems_file = open(file_name, 'w')
        lems_file.write(self.to_xml())
        lems_file.close()
        print("Written LEMS Simulation %s to file: %s"%(self.lems_info['sim_id'], file_name))
        
        return file_name
        
        

if __name__ == '__main__':
    
    sim_id = 'mysim'
    ls = LEMSSimulation(sim_id, 500, 0.05, 'net1')
    ls.include_neuroml2_file('../../examples/NML2_SingleCompHHCell.nml')
    
    disp0 = 'display0'
    ls.create_display(disp0,"Voltages", "-90", "50")
    
    ls.add_line_to_display(disp0, "v", "hhpop[0]/v", "1mV", "#ffffff")
    
    of0 = 'Volts_file'
    ls.create_output_file(of0, "%s.v.dat"%sim_id)
    ls.add_column_to_output_file(of0, 'v', "hhpop[0]/v")
    
    print(ls.lems_info)
    print(ls.to_xml())
    
    ls.save_to_file()
    
    