
import sys
from pyneuroml.analysis import generate_current_vs_frequency_curve
    
nogui = '-nogui' in sys.argv  # Used to supress GUI in tests for Travis-CI
    
generate_current_vs_frequency_curve('NML2_SingleCompHHCell.nml', 
                                    'hhcell', 
                                    0.01, 
                                    0.2, 
                                    0.01, 
                                    1000, 
                                    50,
                                    plot_voltage_traces=not nogui,
                                    plot_if=not nogui)