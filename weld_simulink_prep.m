%% weld_simulink_prep.m — save as file and run
clc;
load('weld_signals.mat');
load('weld_thresholds.mat');

fprintf('Preparing Simulink workspace...\n\n');

sim_normal_I   = [signals.t, signals.I_normal];
sim_normal_V   = [signals.t, signals.V_normal];
sim_spatter_I  = [signals.t, signals.I_spatter];
sim_spatter_V  = [signals.t, signals.V_spatter];
sim_porosity_I = [signals.t, signals.I_porosity];
sim_porosity_V = [signals.t, signals.V_porosity];
sim_unstable_I = [signals.t, signals.I_unstable];
sim_unstable_V = [signals.t, signals.V_unstable];
sim_burn_I     = [signals.t, signals.I_burn];
sim_burn_V     = [signals.t, signals.V_burn];

TH_spatter     = thresholds_struct.spatter_peak;
TH_burn_rms    = thresholds_struct.burn_rms;
TH_instability = thresholds_struct.instability_std;
TH_porosity    = thresholds_struct.porosity_dip;
TH_hf_energy   = thresholds_struct.hf_energy;
SIM_Fs         = thresholds_struct.Fs;
SIM_Ts         = 1 / SIM_Fs;

save('weld_simulink_workspace.mat', ...
     'sim_normal_I',   'sim_normal_V',   ...
     'sim_spatter_I',  'sim_spatter_V',  ...
     'sim_porosity_I', 'sim_porosity_V', ...
     'sim_unstable_I', 'sim_unstable_V', ...
     'sim_burn_I',     'sim_burn_V',     ...
     'TH_spatter', 'TH_burn_rms', 'TH_instability', ...
     'TH_porosity', 'TH_hf_energy', 'SIM_Ts', 'SIM_Fs');

fprintf('============================================\n');
fprintf('  weld_simulink_workspace.mat — SAVED\n');
fprintf('============================================\n');
fprintf('TH_spatter     = %.4f V\n', TH_spatter);
fprintf('TH_burn_rms    = %.4f V\n', TH_burn_rms);
fprintf('TH_instability = %.4f V\n', TH_instability);
fprintf('TH_porosity    = %.4f V\n', TH_porosity);
fprintf('TH_hf_energy   = %.6f\n',   TH_hf_energy);
fprintf('SIM_Ts         = %.6f s\n', SIM_Ts);
fprintf('SIM_Fs         = %.0f Hz\n', SIM_Fs);
fprintf('\nSignal arrays packaged for Simulink:\n');
fprintf('  Current: sim_normal_I / sim_spatter_I / ');
fprintf('sim_porosity_I / sim_unstable_I / sim_burn_I\n');
fprintf('  Voltage: sim_normal_V / sim_spatter_V / ');
fprintf('sim_porosity_V / sim_unstable_V / sim_burn_V\n');
fprintf('\n✓ WEEK 2 FULLY COMPLETE!\n');
fprintf('====================================\n');
fprintf('Next step: Simulink model Week 3\n');
fprintf('  1. Open Simulink\n');
fprintf('  2. New Model → save as weld_monitor.slx\n');
fprintf('  3. Load workspace: load weld_simulink_workspace.mat\n');
fprintf('====================================\n');

% Once you see **"WEEK 2 FULLY COMPLETE!"** — you have 3 `.mat` files ready:
% weld_monitor_project/
% ├── weld_signals.mat              ✓
% ├── weld_thresholds.mat           ✓  
% └── weld_simulink_workspace.mat   ✓ ← new