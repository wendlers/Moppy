difference() {
    cube([20, 20, 15]);
    translate([-2, 2, 2])
        cube([24, 20, 20]);

    union() {
        translate([10, 3, 3.6])
            rotate([90, 0, 0])
                cylinder(r=1.6,  h=5, $fn=100);
        
        translate([10, 3, 10])
            rotate([90, 0, 0])
                cylinder(r=1.6,  h=5, $fn=100);
        
        translate([10-1.6, -2, 3])
            cube([1.6*2, 5, 7]);
    }
    
    translate([10, 12, -2])
        cylinder(r=1.5, h=5, $fn=100);
}