#!/usr/bin/env python

#
#
#   A file which can be run in (Python enabled) NEURON to analyse the rate
#   variables contained in a mod file
#
#

import argparse

import neuron
print("\n\n") 

import matplotlib.pyplot as pylab

from pyneuroml.analysis.NML2ChannelAnalysis import get_state_color

from pylab import *
from math import log


def process_args():
    """ 
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="A script which can be run in (Python enabled) NEURON to analyse the rate variables contained in a mod file")

    parser.add_argument('channel', type=str, metavar='<channel name>', 
                        help='Name of the channel as used by NEURON (i.e. in SUFFIX statement)')
                        
    parser.add_argument('-v',
                        action='store_true',
                        default=False,
                        help="Verbose output")
                        
    parser.add_argument('-nogui',
                        action='store_true',
                        default=False,
                        help="Supress plotting of variables and only save to file")
                        
    parser.add_argument('-minV', 
                        type=int,
                        metavar='<min v>',
                        default=-100,
                        help='Minimum voltage to test (integer, mV)')
                        
    parser.add_argument('-maxV', 
                        type=int,
                        metavar='<max v>',
                        default=100,
                        help='Maximum voltage to test (integer, mV)')
                        
                        
    parser.add_argument('-stepV', 
                        type=int,
                        metavar='<step v>',
                        default=10,
                        help='Voltage step to use (integer, mV)')
                        
    parser.add_argument('-dt', 
                        type=float,
                        metavar='<time step>',
                        default=0.01,
                        help='Timestep for simulations, dt, in ms') #OR -1 for variable time step')
                        
    parser.add_argument('-temperature', 
                        type=float,
                        metavar='<temperature>',
                        default=6.3,
                        help='Temperature (float, celsius)')
                        
    parser.add_argument('-modFile', 
                        type=str,
                        metavar='<name of mod file>',
                        help='Name of the mod file containing the channel')

    
    return parser.parse_args()

    

def main():

    args = process_args()
        
    verbose = args.v
    
    ## Get name of channel mechanism to test

    chanToTest = args.channel
    if verbose: 
        print("Going to test channel: "+ chanToTest)

    ## Create the standard vars h, p for accessing hoc from Python & vice versa

    print("Starting NEURON in Python mode...")
    h = neuron.h
    h.load_file('stdrun.hoc')
    h('''
    objref p
    p = new PythonObject()
    ''')


    h.celsius = args.temperature
        
    ## Create a section, set size & insert pas, passive channel mechanism

    sec = h.Section()

    secname = sec.name()
    sec.L=10
    sec.nseg=1
    for seg in sec :seg.diam = 5

    sec.insert("pas")
    sec(0.5).g_pas = 0.001
    sec(0.5).e_pas = -65


    ## insert channel into section

    sec.insert(str(chanToTest))


    ## Read state variables from mod file

    modFileName = chanToTest+".mod"
    if args.modFile:
        modFileName = args.modFile
    modFile = open(modFileName, 'r')
    inState = 0
    states = []
    for line in modFile:
        if line.count('STATE') > 0:
            inState = 1

        if inState==1:
            if line.count('}') > 0:
                inState = 0
            chopped = line.split()
            for el in chopped:
                if el != '{' and el != '}' and el != 'STATE': 
                    if el.startswith('{'): states.append(el[1:])
                    elif el.endswith('}'): states.append(el[:-1])
                    else: states.append(el)

    if verbose: 
        print("States found in mod file: " + str(states))


    ## Settings for the voltage clamp test

    minV = args.minV
    maxV = args.maxV
    interval = args.stepV
    volts = range(minV,maxV+interval,interval)

    v0 = -0.5                           # Pre holding potential
    preHold = 50                       # and duration
    postHoldStep = 10                  # Post step holding time between steady state checks
    postHoldMax = postHoldStep * 1000   # Max sim run time
    
    timeToCheckTau = preHold + (10*h.dt)


    steadyStateVals = {}
    timeCourseVals = {}
    for s in states:
        steadyStateVals[s] = []
        timeCourseVals[s] = []




    if verbose: 
        figV = pylab.figure()
        figV.canvas.set_window_title("Membrane potentials for %s at %s degC"%(chanToTest,h.celsius))
        plV = figV.add_subplot(111, autoscale_on=True)

        figR = pylab.figure()
        figR.canvas.set_window_title("Rate variables for %s at %s degC"%(chanToTest,h.celsius))
        plR = figR.add_subplot(111, autoscale_on=True)


    for vh in volts:

        tstopMax = preHold + postHoldMax

        h('tstop = '+str(tstopMax))
        h.dt = args.dt
        
        if h.dt == -1:
            h.cvode.active(1)
            h.cvode.atol(0.0001)
            
        # Alternatively use a SEClamp obj
        clampobj = h.SEClamp(.5)
        clampobj.dur1=preHold
        clampobj.amp1=v0
        clampobj.dur2=postHoldMax
        clampobj.amp2=vh
        clampobj.rs=0.001


        tRec = []
        vRec = []
        rateRec = {}
        for s in states:
            rateRec[s] = []

        print("Starting simulation with channel %s of max time: %f, with holding potential: %f"%(chanToTest, tstopMax, vh))
        #h.cvode.active(1)
        h.finitialize(v0)
        tolerance = 1e-5
        lastCheckTime = -1
        lastCheckVal = {}
        initSlopeVal = {}
        foundTau = []
        foundInf = []

        for s in states:
            lastCheckVal[s]=-1e-9
            initSlopeVal[s]=1e9


        while (h.t <= tstopMax) and (len(foundInf) < len(states) or len(foundTau) < len(states)):

            h.fadvance()
            tRec.append(h.t)
            vRec.append(sec(0.5).v)
            vverbose = verbose and False
            if vverbose: 
                print("--- Time: %s; dt: %s; voltage %f; found Tau %s; found Inf %s"%(h.t, h.dt, vh, foundTau, foundInf))
            for s in states:
                rateVal = eval("sec(0.5)."+s+"_"+chanToTest)
                rateRec[s].append(float(rateVal))
                
                if s not in foundTau:
                    if(h.t >= preHold):
                        slope = (rateRec[s][-1] - rateRec[s][-2])/h.dt
                        if initSlopeVal[s] == 0:
                            print("\n**************************************\n*  Error! Initial slope of curve for state %s is 0\n*  Consider using a smaller dt (currently %s) with option: -dt\n**************************************\n"%(s, h.dt))
                        fractOfInit = slope/initSlopeVal[s]
                        if vverbose: 
                            print("        Slope of %s: %s (%s -> %s); init slope: %s; fractOfInit: %s; rateVal: %s"%(s, slope, rateRec[s][-2], rateRec[s][-1], initSlopeVal[s], fractOfInit, rateVal))
                        
                        if initSlopeVal[s]==1e9 and h.t >= timeToCheckTau:
                            initSlopeVal[s] = slope
                            if vverbose: 
                                print("        Init slope of %s: %s at val: %s; timeToCheckTau: %s"%(s, slope, rateVal, timeToCheckTau))
                        elif initSlopeVal[s]!=1e9:

                            if fractOfInit < 0.367879441:
                                tau =  (h.t-timeToCheckTau)  #/ (-1*log(fractOfInit))
                                if vverbose:  
                                    print("        Found! Slope %s: %s, init: %s; at val: %s; time diff %s; fractOfInit: %s; log %s; tau %s"%(s, slope, initSlopeVal[s], rateVal, h.t-timeToCheckTau, fractOfInit, log(fractOfInit), tau))
                                foundTau.append(s)
                                timeCourseVals[s].append(tau)
                            else:
                                if vverbose: 
                                    print("        Not yet fallen by 1/e: %s"% fractOfInit)




            if h.t >= preHold and h.t >= lastCheckTime+postHoldStep:
                if verbose:
                    print("  - Time: %s; dt: %s; voltage %f; found Tau %s; found Inf %s"%(h.t, h.dt, vh, foundTau, foundInf))
                    
                lastCheckTime = h.t

                for s in states:
                    val = eval("sec(0.5)."+s+"_"+chanToTest)

                    if s not in foundInf:
                        if abs((lastCheckVal[s]-val)/val) > tolerance:
                            if verbose: 
                                print("  State %s has failed at %f; lastCheckVal[s] = %f; fract = %f; tolerance = %f"%(s, val, lastCheckVal[s], ((lastCheckVal[s]-val)/val), tolerance))
                        else:
                            if verbose: print("  State %s has passed at %f; lastCheckVal[s] = %f; fract = %f; tolerance = %f"%(s, val, lastCheckVal[s], ((lastCheckVal[s]-val)/val), tolerance))
                            foundInf.append(s)

                        lastCheckVal[s] = val


        if verbose: 
            print("Finished run,  t: %f, v: %f, vh: %f, initSlopeVal: %s, timeCourseVals: %s ---  "%(h.t, sec(0.5).v, vh, str(initSlopeVal), str(timeCourseVals)))

        if verbose: plV.plot(tRec, vRec, solid_joinstyle ='round', solid_capstyle ='round', color='#000000', linestyle='-', marker='None')

        for s in states:
            col=get_state_color(s)
            if verbose: plR.plot(tRec, rateRec[s], solid_joinstyle ='round', solid_capstyle ='round', color=col, linestyle='-', marker='None')

        for s in states:
            val = eval("sec(0.5)."+s+"_"+chanToTest)
            steadyStateVals[s].append(val)



    figRates = pylab.figure()
    plRates = figRates.add_subplot(111, autoscale_on=True)
    figRates.canvas.set_window_title("Steady state(s) of activation variables in %s at %s degC"%(chanToTest,h.celsius))
    pylab.grid('on')

    figTau = pylab.figure()
    figTau.canvas.set_window_title("Time course(s) of activation variables in %s at %s degC"%(chanToTest,h.celsius))
    plTau = figTau.add_subplot(111, autoscale_on=True)
    pylab.grid('on')

    for s in states:
        col=get_state_color(s)

        plRates.plot(volts, steadyStateVals[s], label='%s %s inf'%(chanToTest,s), solid_joinstyle ='round', solid_capstyle ='round', color=col, linestyle='-', marker='o')

        plRates.legend()

        if len(timeCourseVals[s])==len(volts):
            plTau.plot(volts, timeCourseVals[s], label='%s %s tau'%(chanToTest,s), solid_joinstyle ='round', solid_capstyle ='round', color=col, linestyle='-', marker='o')

        plTau.legend()


    for s in states:
        file_name = "%s.%s.inf.dat"%(chanToTest, s)
        file = open(file_name, 'w')
        for i in range(len(volts)):
            file.write("%f\t%f\n"%(volts[i], steadyStateVals[s][i]))
        file.close()
        print("Written info to file: %s"%file_name)

        file_name = "%s.%s.tau.dat"%(chanToTest, s)
        file = open(file_name, 'w')
        for i in range(len(volts)):
            file.write("%f\t%f\n"%(volts[i], timeCourseVals[s][i]))
        file.close()
        print("Written info to file: %s"%file_name)
        
        
    if not args.nogui:
        pylab.show()

    print("Done!")


if __name__ == '__main__':
    main()