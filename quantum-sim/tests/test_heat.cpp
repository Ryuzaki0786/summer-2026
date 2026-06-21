#include "../include/heat_equation.h"
#include <fstream>

int main()
{
    // dx = 1.0/99 ≈ 0.0101,  dx² ≈ 0.000102
    // r = α·dt/dx² = 1.0 · 0.00004 / 0.000102 ≈ 0.39  (≤ 0.5 ✓)
    quantum::HeatEquation heat(1.0, 100, 1.0, 0.00004);
    heat.initialize();

    std::ofstream file("heat.csv");
    for (int n = 0; n < 4000; n++) {
        if (n % 20 == 0) {       // output every 20th step → 200 rows, manageable
            heat.output(file);
        }
        heat.step();
    }
    file.close();
    return 0;
}