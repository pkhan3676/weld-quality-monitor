clc; close all;
load('weld_signals.mat');
load('weld_thresholds.mat');

fprintf('Running Moving RMS + Voltage analysis...\n\n');

window_samples = 1000;
overlap        = 500;
scenarios  = {'normal','spatter','porosity','unstable','burn'};
titles_str = {'Normal','Spatter','Porosity','Arc instability','Burn-through'};
col = [0.12 0.62 0.46; 0.84 0.19 0.19; 0.93 0.50 0.10; 0.33 0.42 0.74; 0.60 0.10 0.60];

rms_stats  = zeros(5,3);
volt_stats = zeros(5,3);

figure('Name','Moving RMS','Position',[50 50 1300 700]);
for k = 1:5
    sig = signals.(['I_' scenarios{k}]);
    N   = length(sig);
    n_w = floor((N - window_samples)/overlap) + 1;
    rms_v = zeros(n_w,1);
    t_rms = zeros(n_w,1);
    for w = 1:n_w
        i1 = (w-1)*overlap + 1;
        i2 = i1 + window_samples - 1;
        rms_v(w) = rms(sig(i1:i2));
        t_rms(w) = signals.t(i1);
    end
    rms_stats(k,:) = [mean(rms_v), max(rms_v), std(rms_v)];
    subplot(2,3,k);
    plot(t_rms, rms_v, 'Color', col(k,:), 'LineWidth', 1.5);
    hold on;
    yline(thresholds_struct.burn_rms,'--r','Burn threshold','FontSize',8);
    hold off;
    xlabel('Time (s)'); ylabel('RMS (V)');
    title(['Moving RMS — ' titles_str{k}]);
    ylim([1.5 2.8]); grid on;
end
sgtitle('Moving RMS (100ms window) — current signal','FontSize',12,'FontWeight','bold');

figure('Name','Voltage Analysis','Position',[100 100 1300 700]);
for k = 1:5
    sig_v = signals.(['V_' scenarios{k}]);
    n_w   = floor((length(sig_v) - window_samples)/overlap) + 1;
    stdv  = zeros(n_w,1);
    minv  = zeros(n_w,1);
    tw    = zeros(n_w,1);
    for w = 1:n_w
        i1 = (w-1)*overlap + 1;
        i2 = i1 + window_samples - 1;
        chunk  = sig_v(i1:i2);
        stdv(w) = std(chunk);
        minv(w) = min(chunk);
        tw(w)   = signals.t(i1);
    end
    volt_stats(k,:) = [mean(sig_v), min(sig_v), mean(stdv)];
    subplot(2,3,k);
    yyaxis left
    plot(tw, stdv, 'Color', col(k,:), 'LineWidth', 1.2);
    ylabel('Std Dev (V)');
    yyaxis right
    plot(tw, minv, '--', 'Color', col(k,:)*0.7, 'LineWidth', 1);
    ylabel('Min V (V)');
    yline(0.80,':r','Porosity dip','FontSize',8);
    xlabel('Time (s)');
    title(['Voltage — ' titles_str{k}]);
    grid on;
end
sgtitle('Voltage std deviation + min value per window','FontSize',12,'FontWeight','bold');

normal_moving_rms = rms_stats(1,1);
normal_volt_std   = volt_stats(1,3);

thresholds_struct.burn_rms        = normal_moving_rms * 1.20;
thresholds_struct.instability_std = normal_volt_std   * 3.50;
thresholds_struct.porosity_dip    = 0.80;
thresholds_struct.window_samples  = window_samples;
thresholds_struct.overlap         = overlap;
thresholds_struct.Fs              = Fs;

save('weld_thresholds.mat','thresholds_struct');

fprintf('====== FINAL SIMULINK THRESHOLDS ======\n');
fprintf('Spatter peak threshold     : %.4f V\n', thresholds_struct.spatter_peak);
fprintf('Burn-through RMS threshold : %.4f V\n', thresholds_struct.burn_rms);
fprintf('Arc instability std thresh : %.4f V\n', thresholds_struct.instability_std);
fprintf('Porosity voltage dip       : %.4f V\n', thresholds_struct.porosity_dip);
fprintf('HF energy threshold        : %.6f\n',   thresholds_struct.hf_energy);
fprintf('Detection window           : %d samples (%.0f ms)\n', window_samples, window_samples/Fs*1000);
fprintf('========================================\n');
fprintf('Week 2 Part 3 complete!\n');