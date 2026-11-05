v {xschem version=3.4.7 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
C {devices/ipin.sym} -200 100 0 0 {name=p1 lab=live_in}
C {devices/ipin.sym} -200 140 0 0 {name=p2 lab=clr}
C {devices/iopin.sym} -200 180 0 0 {name=p3 lab=vdd33}
C {devices/iopin.sym} -200 220 0 0 {name=p4 lab=gnd}
C {devices/opin.sym} -200 260 0 0 {name=p5 lab=live}
C {devices/opin.sym} -200 300 0 0 {name=p6 lab=sticky}
C {sky130_fd_pr/res_xhigh_po_1p41.sym} 0 0 0 0 {name=R1 L=600 model=res_xhigh_po_1p41 spiceprefix=X mult=1}
C {devices/lab_pin.sym} 0 -30 0 0 {name=p7 sig_type=std_logic lab=vdd33}
C {devices/lab_pin.sym} 0 30 0 0 {name=p8 sig_type=std_logic lab=vcl}
C {devices/lab_pin.sym} -20 0 0 0 {name=p9 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 120 0 0 0 {name=M1 L=0.5 W=4 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 140 -30 0 0 {name=p10 sig_type=std_logic lab=vcl}
C {devices/lab_pin.sym} 100 0 0 0 {name=p11 sig_type=std_logic lab=vcl}
C {devices/lab_pin.sym} 140 30 0 0 {name=p12 sig_type=std_logic lab=c1}
C {devices/lab_pin.sym} 140 0 0 0 {name=p13 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 240 0 0 0 {name=M2 L=0.5 W=4 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 260 -30 0 0 {name=p14 sig_type=std_logic lab=c1}
C {devices/lab_pin.sym} 220 0 0 0 {name=p15 sig_type=std_logic lab=c1}
C {devices/lab_pin.sym} 260 30 0 0 {name=p16 sig_type=std_logic lab=c2}
C {devices/lab_pin.sym} 260 0 0 0 {name=p17 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 360 0 0 0 {name=M3 L=0.5 W=4 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 380 -30 0 0 {name=p18 sig_type=std_logic lab=c2}
C {devices/lab_pin.sym} 340 0 0 0 {name=p19 sig_type=std_logic lab=c2}
C {devices/lab_pin.sym} 380 30 0 0 {name=p20 sig_type=std_logic lab=gnd}
C {devices/lab_pin.sym} 380 0 0 0 {name=p21 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 480 0 0 0 {name=M4 L=0.5 W=4 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 500 -30 0 0 {name=p22 sig_type=std_logic lab=vdd33}
C {devices/lab_pin.sym} 460 0 0 0 {name=p23 sig_type=std_logic lab=vcl}
C {devices/lab_pin.sym} 500 30 0 0 {name=p24 sig_type=std_logic lab=vlim}
C {devices/lab_pin.sym} 500 0 0 0 {name=p25 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/res_xhigh_po_1p41.sym} 600 0 0 0 {name=R2 L=1200 model=res_xhigh_po_1p41 spiceprefix=X mult=1}
C {devices/lab_pin.sym} 600 -30 0 0 {name=p26 sig_type=std_logic lab=vlim}
C {devices/lab_pin.sym} 600 30 0 0 {name=p27 sig_type=std_logic lab=gnd}
C {devices/lab_pin.sym} 580 0 0 0 {name=p28 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/cap_mim_m3_1.sym} 720 0 0 0 {name=C1 model=cap_mim_m3_1 W=10 L=10 MF=1 spiceprefix=X}
C {devices/lab_pin.sym} 720 -30 0 0 {name=p29 sig_type=std_logic lab=vlim}
C {devices/lab_pin.sym} 720 30 0 0 {name=p30 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 840 420 0 0 {name=M5 L=0.5 W=4 nf=1 mult=1 model=pfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 860 390 0 0 {name=p31 sig_type=std_logic lab=vdd33}
C {devices/lab_pin.sym} 820 420 0 0 {name=p32 sig_type=std_logic lab=live_in}
C {devices/lab_pin.sym} 860 450 0 0 {name=p33 sig_type=std_logic lab=sb}
C {devices/lab_pin.sym} 860 420 0 0 {name=p34 sig_type=std_logic lab=vdd33}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 840 560 0 0 {name=M6 L=0.5 W=2 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 860 530 0 0 {name=p35 sig_type=std_logic lab=sb}
C {devices/lab_pin.sym} 820 560 0 0 {name=p36 sig_type=std_logic lab=live_in}
C {devices/lab_pin.sym} 860 590 0 0 {name=p37 sig_type=std_logic lab=gnd}
C {devices/lab_pin.sym} 860 560 0 0 {name=p38 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 960 420 0 0 {name=M7 L=0.5 W=2 nf=1 mult=1 model=pfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 980 390 0 0 {name=p39 sig_type=std_logic lab=vdd33}
C {devices/lab_pin.sym} 940 420 0 0 {name=p40 sig_type=std_logic lab=clr}
C {devices/lab_pin.sym} 980 450 0 0 {name=p41 sig_type=std_logic lab=rb}
C {devices/lab_pin.sym} 980 420 0 0 {name=p42 sig_type=std_logic lab=vdd33}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 960 560 0 0 {name=M8 L=0.5 W=1 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 980 530 0 0 {name=p43 sig_type=std_logic lab=rb}
C {devices/lab_pin.sym} 940 560 0 0 {name=p44 sig_type=std_logic lab=clr}
C {devices/lab_pin.sym} 980 590 0 0 {name=p45 sig_type=std_logic lab=gnd}
C {devices/lab_pin.sym} 980 560 0 0 {name=p46 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1080 420 0 0 {name=M9 L=0.5 W=2 nf=1 mult=1 model=pfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1100 390 0 0 {name=p47 sig_type=std_logic lab=vdd33}
C {devices/lab_pin.sym} 1060 420 0 0 {name=p48 sig_type=std_logic lab=sb}
C {devices/lab_pin.sym} 1100 450 0 0 {name=p49 sig_type=std_logic lab=q}
C {devices/lab_pin.sym} 1100 420 0 0 {name=p50 sig_type=std_logic lab=vdd33}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1200 420 0 0 {name=M10 L=0.5 W=2 nf=1 mult=1 model=pfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1220 390 0 0 {name=p51 sig_type=std_logic lab=vdd33}
C {devices/lab_pin.sym} 1180 420 0 0 {name=p52 sig_type=std_logic lab=qb}
C {devices/lab_pin.sym} 1220 450 0 0 {name=p53 sig_type=std_logic lab=q}
C {devices/lab_pin.sym} 1220 420 0 0 {name=p54 sig_type=std_logic lab=vdd33}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1080 560 0 0 {name=M11 L=0.5 W=2 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1100 530 0 0 {name=p55 sig_type=std_logic lab=q}
C {devices/lab_pin.sym} 1060 560 0 0 {name=p56 sig_type=std_logic lab=sb}
C {devices/lab_pin.sym} 1100 590 0 0 {name=p57 sig_type=std_logic lab=n_q}
C {devices/lab_pin.sym} 1100 560 0 0 {name=p58 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1200 560 0 0 {name=M12 L=0.5 W=2 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1220 530 0 0 {name=p59 sig_type=std_logic lab=n_q}
C {devices/lab_pin.sym} 1180 560 0 0 {name=p60 sig_type=std_logic lab=qb}
C {devices/lab_pin.sym} 1220 590 0 0 {name=p61 sig_type=std_logic lab=gnd}
C {devices/lab_pin.sym} 1220 560 0 0 {name=p62 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1320 420 0 0 {name=M13 L=0.5 W=2 nf=1 mult=1 model=pfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1340 390 0 0 {name=p63 sig_type=std_logic lab=vdd33}
C {devices/lab_pin.sym} 1300 420 0 0 {name=p64 sig_type=std_logic lab=rb}
C {devices/lab_pin.sym} 1340 450 0 0 {name=p65 sig_type=std_logic lab=qb}
C {devices/lab_pin.sym} 1340 420 0 0 {name=p66 sig_type=std_logic lab=vdd33}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1440 420 0 0 {name=M14 L=0.5 W=2 nf=1 mult=1 model=pfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1460 390 0 0 {name=p67 sig_type=std_logic lab=vdd33}
C {devices/lab_pin.sym} 1420 420 0 0 {name=p68 sig_type=std_logic lab=q}
C {devices/lab_pin.sym} 1460 450 0 0 {name=p69 sig_type=std_logic lab=qb}
C {devices/lab_pin.sym} 1460 420 0 0 {name=p70 sig_type=std_logic lab=vdd33}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1320 560 0 0 {name=M15 L=0.5 W=2 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1340 530 0 0 {name=p71 sig_type=std_logic lab=qb}
C {devices/lab_pin.sym} 1300 560 0 0 {name=p72 sig_type=std_logic lab=rb}
C {devices/lab_pin.sym} 1340 590 0 0 {name=p73 sig_type=std_logic lab=n_qb}
C {devices/lab_pin.sym} 1340 560 0 0 {name=p74 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1440 560 0 0 {name=M16 L=0.5 W=2 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1460 530 0 0 {name=p75 sig_type=std_logic lab=n_qb}
C {devices/lab_pin.sym} 1420 560 0 0 {name=p76 sig_type=std_logic lab=q}
C {devices/lab_pin.sym} 1460 590 0 0 {name=p77 sig_type=std_logic lab=gnd}
C {devices/lab_pin.sym} 1460 560 0 0 {name=p78 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1560 420 0 0 {name=M17 L=0.5 W=2 nf=1 mult=1 model=pfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1580 390 0 0 {name=p79 sig_type=std_logic lab=vdd33}
C {devices/lab_pin.sym} 1540 420 0 0 {name=p80 sig_type=std_logic lab=q}
C {devices/lab_pin.sym} 1580 450 0 0 {name=p81 sig_type=std_logic lab=qn}
C {devices/lab_pin.sym} 1580 420 0 0 {name=p82 sig_type=std_logic lab=vdd33}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1560 560 0 0 {name=M18 L=0.5 W=1 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1580 530 0 0 {name=p83 sig_type=std_logic lab=qn}
C {devices/lab_pin.sym} 1540 560 0 0 {name=p84 sig_type=std_logic lab=q}
C {devices/lab_pin.sym} 1580 590 0 0 {name=p85 sig_type=std_logic lab=gnd}
C {devices/lab_pin.sym} 1580 560 0 0 {name=p86 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1680 840 0 0 {name=M19 L=0.5 W=12 nf=1 mult=1 model=pfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1700 810 0 0 {name=p87 sig_type=std_logic lab=vlim}
C {devices/lab_pin.sym} 1660 840 0 0 {name=p88 sig_type=std_logic lab=sb}
C {devices/lab_pin.sym} 1700 870 0 0 {name=p89 sig_type=std_logic lab=live}
C {devices/lab_pin.sym} 1700 840 0 0 {name=p90 sig_type=std_logic lab=vlim}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1680 980 0 0 {name=M20 L=0.5 W=2 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1700 950 0 0 {name=p91 sig_type=std_logic lab=live}
C {devices/lab_pin.sym} 1660 980 0 0 {name=p92 sig_type=std_logic lab=sb}
C {devices/lab_pin.sym} 1700 1010 0 0 {name=p93 sig_type=std_logic lab=gnd}
C {devices/lab_pin.sym} 1700 980 0 0 {name=p94 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 1800 840 0 0 {name=M21 L=0.5 W=12 nf=1 mult=1 model=pfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1820 810 0 0 {name=p95 sig_type=std_logic lab=vlim}
C {devices/lab_pin.sym} 1780 840 0 0 {name=p96 sig_type=std_logic lab=qn}
C {devices/lab_pin.sym} 1820 870 0 0 {name=p97 sig_type=std_logic lab=sticky}
C {devices/lab_pin.sym} 1820 840 0 0 {name=p98 sig_type=std_logic lab=vlim}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 1800 980 0 0 {name=M22 L=0.5 W=2 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 1820 950 0 0 {name=p99 sig_type=std_logic lab=sticky}
C {devices/lab_pin.sym} 1780 980 0 0 {name=p100 sig_type=std_logic lab=qn}
C {devices/lab_pin.sym} 1820 1010 0 0 {name=p101 sig_type=std_logic lab=gnd}
C {devices/lab_pin.sym} 1820 980 0 0 {name=p102 sig_type=std_logic lab=gnd}
