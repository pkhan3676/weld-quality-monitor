% Save as: burn_detection_test.m and run

load('weld_simulink_workspace.mat');

fprintf('Testing burn-through detection...\n\n');

% Manual moving RMS calculation
n = length(sim_burn_I);
window = 1000;
rms_vals = zeros(n,1);

for i = 1:n
    i_start = max(1, i - window + 1);
    rms_vals(i) = rms(sim_burn_I(i_start:i, 2));
end

% Detection
alert = double(rms_vals > TH_burn_rms);
detected_samples = sum(alert);

fprintf('TH_burn_rms     = %.4f V\n', TH_burn_rms);
fprintf('Max RMS value   = %.4f V\n', max(rms_vals));
fprintf('Samples detected= %d\n', detected_samples);

if detected_samples > 0
    fprintf('\n✓ BURN-THROUGH DETECTED SUCCESSFULLY!\n');
else
    fprintf('\n✗ Not detected\n');
end

% Plot
figure('Name','Burn Detection','Position',[100 100 1000 600]);

subplot(3,1,1);
plot(sim_burn_I(:,1), sim_burn_I(:,2),'b','LineWidth',0.8);
yline(TH_burn_rms,'r--','LineWidth',2);
title('Current signal — burn-through');
ylabel('Voltage (V)'); grid on;

subplot(3,1,2);
plot(sim_burn_I(:,1), rms_vals,'m','LineWidth',1.5);
yline(TH_burn_rms,'r--','Threshold','LineWidth',2);
title('Moving RMS (100ms window)');
ylabel('RMS (V)'); grid on;

subplot(3,1,3);
area(sim_burn_I(:,1), alert,'FaceColor','r','FaceAlpha',0.6);
title('BURN ALERT — 1 = Detected!');
ylabel('Alert'); xlabel('Time (s)');
ylim([-0.2 1.5]); grid on;

sgtitle('Weld Burn-Through Detection Result','FontSize',13,'FontWeight','bold');