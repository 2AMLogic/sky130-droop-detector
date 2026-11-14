v {xschem version=3.4.7 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
C {devices/ipin.sym} -200 100 0 0 {name=p1 lab=flag_in}
C {devices/iopin.sym} -200 140 0 0 {name=p2 lab=vdd33}
C {devices/iopin.sym} -200 180 0 0 {name=p3 lab=gnd}
C {devices/opin.sym} -200 220 0 0 {name=p4 lab=flag_f}
C {sky130_fd_pr/res_xhigh_po_1p41.sym} 0 0 0 0 {name=R1 L=3 model=res_xhigh_po_1p41 spiceprefix=X mult=1}
C {devices/lab_pin.sym} 0 -30 0 0 {name=p5 sig_type=std_logic lab=flag_in}
C {devices/lab_pin.sym} 0 30 0 0 {name=p6 sig_type=std_logic lab=rc}
C {devices/lab_pin.sym} -20 0 0 0 {name=p7 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/cap_mim_m3_1.sym} 120 0 0 0 {name=C1 model=cap_mim_m3_1 W=9 L=9 MF=1 spiceprefix=X}
C {devices/lab_pin.sym} 120 -30 0 0 {name=p8 sig_type=std_logic lab=rc}
C {devices/lab_pin.sym} 120 30 0 0 {name=p9 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 240 280 0 0 {name=M1 L=0.5 W=2 nf=1 mult=1 model=pfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 260 250 0 0 {name=p10 sig_type=std_logic lab=vdd33}
C {devices/lab_pin.sym} 220 280 0 0 {name=p11 sig_type=std_logic lab=rc}
C {devices/lab_pin.sym} 260 310 0 0 {name=p12 sig_type=std_logic lab=rcb}
C {devices/lab_pin.sym} 260 280 0 0 {name=p13 sig_type=std_logic lab=vdd33}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 240 420 0 0 {name=M2 L=0.5 W=1 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 260 390 0 0 {name=p14 sig_type=std_logic lab=rcb}
C {devices/lab_pin.sym} 220 420 0 0 {name=p15 sig_type=std_logic lab=rc}
C {devices/lab_pin.sym} 260 450 0 0 {name=p16 sig_type=std_logic lab=gnd}
C {devices/lab_pin.sym} 260 420 0 0 {name=p17 sig_type=std_logic lab=gnd}
C {sky130_fd_pr/pfet_g5v0d10v5.sym} 360 280 0 0 {name=M3 L=0.5 W=2 nf=1 mult=1 model=pfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 380 250 0 0 {name=p18 sig_type=std_logic lab=vdd33}
C {devices/lab_pin.sym} 340 280 0 0 {name=p19 sig_type=std_logic lab=rcb}
C {devices/lab_pin.sym} 380 310 0 0 {name=p20 sig_type=std_logic lab=flag_f}
C {devices/lab_pin.sym} 380 280 0 0 {name=p21 sig_type=std_logic lab=vdd33}
C {sky130_fd_pr/nfet_g5v0d10v5.sym} 360 420 0 0 {name=M4 L=0.5 W=1 nf=1 mult=1 model=nfet_g5v0d10v5 spiceprefix=X}
C {devices/lab_pin.sym} 380 390 0 0 {name=p22 sig_type=std_logic lab=flag_f}
C {devices/lab_pin.sym} 340 420 0 0 {name=p23 sig_type=std_logic lab=rcb}
C {devices/lab_pin.sym} 380 450 0 0 {name=p24 sig_type=std_logic lab=gnd}
C {devices/lab_pin.sym} 380 420 0 0 {name=p25 sig_type=std_logic lab=gnd}
