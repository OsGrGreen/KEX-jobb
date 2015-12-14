import numpy as np
import itertools
import allensdk.model.GLM as GLM
import logging
import statsmodels.api as sm

def ASGLM_pairwise(ks_int, I_stim, voltage, spike_ind, cinit, tauinit, SCL, dt, resting_potential,fit_phrase, 
                   SHORT_RUN=False, MAKE_PLOT=False, SHOW_PLOT=False, BLOCK=False):
    '''
    input:
        ks_int: initial possible k's
        '''
    if fit_phrase not in ['asc', 'ascR', 'ascREl', 'ascRElC']:
        raise Exception("The fit phrase is does not fit available fitting options")
    
    #TODO; MAKE SURE CLARIFY WHETHER LIST APPENDS ARE OVER PAIRWISE K'S OR REPEATS
    #TODO: ISTIM WAS ORIGINALLY AN AMPLITUTE EPOCH
    #Initial tau and C as seed inputs for optimization
#                    cinit = 130.e-12
#                    tauinit = 25.e-3
    
    #TODO: get rid of hard coding
    #Initialize post-spike filter parameters (MOST OF THESE ARE HARD-CODED currently)
    nkt = 8000                  # arbitrary length of filter  WANT FILTER TO COVER A LENGTH OF TIME, WANT FILTER TO BE LONGER THAN LONGEST LENGTH ASC 
    DTsim = dt                  #DTsim = dt means filter is nkt*dt = 100 ms long in this case THIS SHOULD INDEED BE THE SAMPLE WIDTH
    neye = 0                    #no of identity basis vectors DELTA
    f = 1e-3/dt                 #pre-factor for getting time units correct for bases

    #TODO: THIS IS SOME FUNKY CONVERSIONS
#   taus_int = [5,10,25]     #positions of peaks (in ms) fns!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    taus_int=[1000./kk for kk in ks_int] #converting to ms
    taus_filter = [f*j for j in taus_int]     #convert ms time to filter time units 1/(dt*ks)
    ks_list = [(1.0/(i)) for i in taus_filter]        #use peak positions of rcos bumps as time-scales for exponential bases
    ncos = 2                    #no of bases!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    flag_exp = 1                #flag_exp = 1 means use exponential bases, else use raised-cosine bumps 
    vL = resting_potential
    
    #----GLM fit with post-spike currents
    
    tst = 0 #190000#355000    #time-step to start
    #tend = len(I_stim) #300000#430000   #time-step to end MOVING INTO FOR LOOPS BECAUSE I STIM IS NOW A LIST
    npcut = int(SCL)  # no of points to cut after each spike-initiation
    
    #Collect spikes between tst and tend  
    t0_list = []
    for mm in range(len(I_stim)):
        tend = len(I_stim[mm])
        t0=[]
        #RAMS STARTED HERE INTENTION OF FINDING SPIKES AT A GIVEN AMPLITUTE OF NOISE (ORIGINALLY RAM RAN THIS MANUALLY BY CHANING TSTART AND TEND)
        for jj in range(len(spike_ind[mm])):  
            if spike_ind[mm][jj]>tst and spike_ind[mm][jj]<tend:
                t0.append(spike_ind[mm][jj])
        
        t0_list.append(t0)
    
   
    ######NEW PAIRWISE COMBINATION OF BASIS VECTORS STARTS HERE#################
    #Create a list of pairs of ks (NOTE: import itertools in header)
    ks_pairs = list(itertools.combinations(ks_list,ncos)) 
    ks_pairs_in_SI_units= list(itertools.combinations(ks_int, ncos))   
    if len(ks_pairs)!=10:
        raise Exception('figure subplots will need to be changed as there is a different number than 10 ks_pairs.')
    
    #Initialize list to hold charge dump values and amp-vectors
    fitprs_list = []
    llf_list = []
    R_list = []
    #Iterate over all pairs
    if SHORT_RUN:
        logging.warning("You are not doing all the ks pairs in ASGLM_pairwise")
        ks_pairs=[ks_pairs[0]]

    R_for_all_ks_pairs=[]
    asc_amp_for_all_ks_pairs=[]
    El_for_all_ks_pairs=[] 
    C_for_all_ks_pairs=[]
    llh_for_all_ks_pairs=[]
    for ks_ind, (ks_fit_units, ks_SI_units) in enumerate(zip(ks_pairs, ks_pairs_in_SI_units)):
        print 'ks_fit_units', ks_fit_units
        #Create basis IPSPs
        #!!!!!!!!!!!!!no need to touch these!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        if MAKE_PLOT:
            plotting_colors=['r', 'b', 'g', 'm', 'c']
            plt.figure(78, figsize=(20,10))
        basis_IPSP_list = []
        for rr in range(len(I_stim)): #loop over repeats
            #NOTE ONLY ONE OF TAUS_FILTER AND ks_fit_units ARE EXCLUSIVE DEPENDING ONE WHETHER USING BUMPS OR EXP DECAY==CHECK THIS~!!!!
            #find the basis of the entire trace
            basis_IPSP, gg0 = GLM.create_basis_IPSP(neye,ncos,taus_filter,ks_fit_units,DTsim,t0_list[rr],I_stim[rr],nkt,flag_exp,npcut)
            basis_IPSP_list.append(basis_IPSP) 
            #--Plot basis IPSPs between si and se    
            si = t0_list[0][0]-10   #plot start_ind
            se = si+nkt+10  #plot end_ind
            tvec = dt*np.arange(si-tst,se-tst)   #convert time-steps to real time (in sec)        
            if MAKE_PLOT:
                plt.figure(78)
                plt.subplot(5,2, ks_ind+1)
                plt.plot(1e3*tvec,basis_IPSP[si:se,:], lw=2, label=str(rr)) #1e3 plots time on x-axis in ms
                plt.xlabel('time (ms)')
                plt.title("k's "+str(ks_SI_units))
        if MAKE_PLOT:
            plt.annotate('ASGLM (fit asc and R): AScurrent basis',
                         xy=(.4, .985),
                         xycoords='figure fraction',
                         horizontalalignment='left', verticalalignment='top',
                         fontsize=20)
            plt.legend()
            plt.tight_layout()
                
        if SHOW_PLOT:
            plt.show(block=BLOCK)                                      
        
        #Not sure I want to fit them all together yet
#        def combine_sweeps():
#            '''Created this function to ensure I wast using local variables later in the code.
#            Creates one long spikeless train'''
#            if MAKE_PLOT:
#                plt.figure(figsize=(20, 10))
#            plt.figure()
#            
#            #Unsmoothed raw data
#            i_all_swps_list = []
#            b_ipsp_all_swps_list = []
#            v_all_swps_list = []
#            dv_all_swps_list = []
#            
#            for ss in range(len(I_stim)): #loop over repeats
#                tend = len(I_stim[ss])
#                i = I_stim[ss][tst:tend-1]
#                b_ipsp = basis_IPSP_list[ss][tst:tend-1]
#                
#                #!!!!!!!!!!!!!specify reset as rest of code!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#                v = voltage[ss][tst:tend-1]    
#                vs = voltage[ss][tst+1:tend]
#                dv = (vs-v)/dt                  #derivative of voltage
#                
#                #delete npcut points after spike from each qty    
#                delpts = []
#                for kk in range(len(t0_list[ss])):
#                    delpts.append(range(int(t0_list[ss][kk])-tst,int(t0_list[ss][kk])-tst+npcut))
#                
#                dv = np.delete(dv,delpts,0)
#                v = np.delete(v,delpts,0)
#                i = np.delete(i,delpts,0)
#                b_ipsp = np.delete(b_ipsp,delpts,0)
#                
#                v_all_swps_list.append(v)
#                dv_all_swps_list.append(dv)
#                i_all_swps_list.append(i)
#                b_ipsp_all_swps_list.append(b_ipsp)
#               
#                #concatenating sweeps together inorder to fit them all at once
#                v_all_swps=np.concatenate(v_all_swps_list)
#                dv_all_swps=np.concatenate(dv_all_swps_list)
#                i_all_swps=np.concatenate(i_all_swps_list)
#                b_ipsp_all_swps=np.concatenate(b_ipsp_all_swps_list)
#            
#                    #Plot voltage (after spike-cutting) from tst to tend as fn of time (in ms)
#                tvec = dt*np.arange(len(v))
#                if MAKE_PLOT:
#                    plt.plot(tvec,v)
#                    plt.xlabel('time (s)')
#                    plt.ylabel('voltage (V)')
#            if MAKE_PLOT:
#                plt.title('Spike removed noise')
#            if SHOW_PLOT:
#                plt.show(block=BLOCK)
#                
#            return i_all_swps_list, b_ipsp_all_swps_list, v_all_swps_list, dv_all_swps_list
#        
#        (i_all_swps_list, b_ipsp_all_swps_list, v_all_swps_list, dv_all_swps_list)=combine_sweeps()

        #--cut spikes out of dv, v, i, and b_ipsp
        #--and put the different sweeps in lists
#         if MAKE_PLOT:
#             plt.figure(figsize=(20, 10))
        i_all_swps_list = []
        b_ipsp_all_swps_list = []
        v_all_swps_list = []
        dv_all_swps_list = []        
        for ss in range(len(I_stim)): #loop over repeats
            tend = len(I_stim[ss])
            i = I_stim[ss][tst:tend-1]
            b_ipsp = basis_IPSP_list[ss][tst:tend-1]
            
            #!!!!!!!!!!!!!specify reset as rest of code!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            v = voltage[ss][tst:tend-1]    
            vs = voltage[ss][tst+1:tend]
            dv = (vs-v)/dt                  #derivative of voltage
            
            #delete npcut points after spike from each qty    
            delpts = []
            for kk in range(len(t0_list[ss])):
                delpts.append(range(int(t0_list[ss][kk])-tst,int(t0_list[ss][kk])-tst+npcut))
            
            dv = np.delete(dv,delpts,0)
            v = np.delete(v,delpts,0)
            i = np.delete(i,delpts,0)
            b_ipsp = np.delete(b_ipsp,delpts,0)
            
            v_all_swps_list.append(v)
            dv_all_swps_list.append(dv)
            i_all_swps_list.append(i)
            b_ipsp_all_swps_list.append(b_ipsp)
            
            tvec = dt*np.arange(len(v))
#             if MAKE_PLOT:
#                 plt.subplot(4,1,1)
#                 plt.plot(tvec, i*1e12, label=str(ss))
#                 plt.ylabel('current (pA)')
#                 plt.subplot(4,1,2)
#                 plt.plot(tvec,v*1e3)
#                 plt.ylabel('voltage (mV)')
#                 plt.subplot(4,1,3)
#                 plt.plot(tvec, dv)
#                 plt.ylabel('dv/dt')
#                 plt.subplot(4,1,4)
#                 plt.plot(tvec, b_ipsp)
#                 plt.ylabel('asc basis')
#                 plt.xlabel('time (s)')
#                 
#         if MAKE_PLOT:
#             plt.annotate('Spike removed noise',
#                          xy=(.4, .985),
#                          xycoords='figure fraction',
#                          horizontalalignment='left', verticalalignment='top',
#                          fontsize=20)
#             plt.legend()
#         if SHOW_PLOT:
#             plt.show(block=BLOCK)
        
        #HERE I NEED TO CHANGE THINGS to be able to fit:just asc, asc+r, asc+r+el, asc+r+el+c
        #Set up and perform GLM fit for AS currents 
        #Fit computes the amplitude of each basis AS current
        # WHAT IS BEING FIT IS ON RIGHT.
        if MAKE_PLOT:
            plt.figure(79, figsize=(20, 12))
            plt.figure(80, figsize=(20, 12))
        R_for_each_sweep=[]
        asc_amp_for_each_sweep=[]
        El_for_each_sweep=[]
        C_for_each_sweep=[]
        llh_for_each_sweep=[]
        for kkk, (v_spike_deleted, dv_spike_deleted, i_spike_deleted, b_ipsp_spikes_deleted) in \
            enumerate(zip(v_all_swps_list, dv_all_swps_list, i_all_swps_list, b_ipsp_all_swps_list)):
        
        #--FITTING ASC
#         inp = np.zeros((len(i_all_swps),ncos+1))
#         inp[:,range(0,ncos)] = (1/cinit)*b_ipsp_all_swps[:,range(ncos)]
#         #inp[:,ncos] = -(v_all_swps-vL)/tauinit
#         #inp[:,ncos+1] = i/cinit
#         out = dv_all_swps -i_all_swps/cinit + (v_all_swps-vL)/tauinit
        
            #--FITTING ASC AND R
            #--Here fitprs will have the amp of asc followed by R
            inp = np.zeros((len(i_spike_deleted),ncos+1))
            inp[:,range(0,ncos)] = (1/cinit)*b_ipsp_spikes_deleted[:,range(ncos)]
            inp[:,ncos] = -(v_spike_deleted-vL)/tauinit
            #inp[:,ncos+1] = i/cinit
            out = dv_spike_deleted -i_spike_deleted/cinit#+ (v-vL)/tauinit - i/cinit
        
#         #--FITTING ASC AND R & C
#         inp = np.zeros((len(i_all_swps),ncos+2))
#         inp[:,range(0,ncos)] = (1/cinit)*b_ipsp_all_swps[:,range(ncos)]
#         inp[:,ncos] = -(v_all_swps-vL)/tauinit
#         inp[:,ncos+1] = i_all_swps/cinit
#         out = dv_all_swps#+ (v-vL)/tauinit - i/cinit    
        
#         #--FITTING ASC AND R & C & El
#         inp = np.zeros((len(i_all_swps),ncos+1))
#         inp[:,range(0,ncos)] = (1/cinit)*b_ipsp_all_swps[:,range(ncos)]
#         inp[:,ncos] = -(v_all_swps-vL)/tauinit
#         inp[:,ncos+1] = i_all_swps/cinit
#         inp = sm.add_constant(inp, prepend = False)
#         out = dv_all_swps#+ (v-vL)/tauinit - i/cinit   
#        #print 'fit_C(pF)', 1e12*cinit/fitprs[ncos+1]
#        #print 'El* (mV)' 1e3*(fitprs[ncos+2]*tauinit/fitprs[ncos]) 

            try:
                glm_fit = sm.GLM(out,inp,family=sm.families.Gaussian(sm.families.links.identity))
                res = glm_fit.fit()
                fitprs = res.params  #[AMP OF ASC, TAU]
                llh=res.llf
                fit_R=tauinit/(fitprs[ncos]*cinit)
                fit_asc_amp=fitprs[:ncos]
#                print 'fit_tau(ms)', 1e3*tauinit/fitprs[ncos]
#                print 'fit_R (mohms)', 1e-6*fit_R
#                print 'specified C (pF)', 1e12*cinit
                #Compute and plot post-spike current
                #(essentially multiply basis functions with correct amplitudes from GLM fit)
                ipsc = np.sum(b_ipsp_spikes_deleted[:,0:ncos]*fit_asc_amp,1)  #THIS IS TOTAL POSTSPIKE CURRENT
            except Exception, e:
                logging.warning("fit didn't work: " + str(e))
                llh=np.nan
                fit_R=np.NAN
                fit_asc_amp=np.ones(ncos)*np.NAN
                ipsc=np.ones(len(b_ipsp_spikes_deleted[:,0]))*np.NAN
                
            R_for_each_sweep.append(fit_R)
            asc_amp_for_each_sweep.append(fit_asc_amp)
            El_for_each_sweep.append(None)  
            C_for_each_sweep.append(None)
            llh_for_each_sweep.append(llh)
            
            #Plot a single instance of AS current as function of time (in ms)
            if MAKE_PLOT:
                plt.figure(79)
                plt.subplot(5,2, ks_ind+1)
                plot_inds = np.arange(int(t0_list[0][0])-tst,int(t0_list[0][0])-tst+nkt) #plot just after first spike
                tvec = dt*plot_inds
                plt.plot(tvec,ipsc[plot_inds], lw=2, label='llh='+str(llh))
                plt.xlabel('time (s)')
                plt.ylabel('current (A)')
                plt.title("k's "+str(ks_SI_units))
                
                plt.figure(80)
                plt.subplot(5,2,ks_ind+1)
                for ASC, KS in zip(fit_asc_amp, np.array(ks_SI_units)):
                #TODO: MAKE SURE I SHOULD BE USING SI UNITS HERE {I think this is correct as it is what I am returning from the function]
                #TODO: MAKE SURE THE SIGNS OF K ARE OK
                    t_plot=np.arange(10000)*dt
                    single_asc_trace=ASC*np.exp(-KS*t_plot)
                    plt.plot(t_plot, single_asc_trace, lw=2, label='sweep '+str(kkk))
                plt.xlabel('time (s)')
                plt.ylabel('current (A)')
                plt.title("k's "+str(ks_SI_units))

        if MAKE_PLOT:
            plt.figure(79)
            plt.tight_layout()
            plt.annotate('ASGLM (fit asc and R): Sum fit after spike currents',
                         xy=(.3, .985),
                         xycoords='figure fraction',
                         horizontalalignment='left', verticalalignment='top',
                         fontsize=20)
            plt.legend()
            
            plt.figure(80)
            plt.tight_layout()
            plt.annotate('ASGLM (fit asc and R): Individual Currents',
                         xy=(.3, .985),
                         xycoords='figure fraction',
                         horizontalalignment='left', verticalalignment='top',
                         fontsize=20)
            plt.legend()
        if SHOW_PLOT:
            plt.show(block=False)
        
        
#        #BELOW IS OVER EVERY PAIR
#        R_list.append(tauinit/(fitprs[ncos]*cinit))  
#        fitprs_list.append(fitprs[:ncos])
#        llf_list.append(res.llf)
        R_for_all_ks_pairs.append(R_for_each_sweep)
        asc_amp_for_all_ks_pairs.append(asc_amp_for_each_sweep)
        El_for_all_ks_pairs.append(El_for_each_sweep)
        C_for_all_ks_pairs.append(C_for_each_sweep)
        llh_for_all_ks_pairs.append(llh_for_each_sweep)

        #!!!!!!!!!!!!!we multiplied ks by dt for SI!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!     
    ave_llh_for_each_pair=np.mean(llh_for_all_ks_pairs, axis=1)
    best_ks_pair_ind = np.where(np.max(ave_llh_for_each_pair)==ave_llh_for_each_pair)[0][0]

    best_k_pair=np.array(ks_pairs[best_ks_pair_ind])/dt
    best_asc_amp=np.array(asc_amp_for_all_ks_pairs[best_ks_pair_ind])
    best_R=np.array(R_for_all_ks_pairs[best_ks_pair_ind])
    best_C=np.array(C_for_all_ks_pairs[best_ks_pair_ind])
    best_El=np.array(El_for_all_ks_pairs[best_ks_pair_ind])
    best_llh=np.array(llh_for_all_ks_pairs[best_ks_pair_ind])

    print '**********from ASGLM_pairwise******************************************'
    print 'best_ks_pair_ind', best_ks_pair_ind
    print 'best_asc_amp', best_asc_amp
    print 'best_k_pair', best_k_pair
    print 'best_R', best_R 
    print 'best_C', best_C 
    print 'best_El', best_El
    print 'best_llh', best_llh
        
    print '**********done with ASGLM_pairwise***********************************'
    
    return best_k_pair, best_asc_amp, best_R, best_C, best_El, best_llh
