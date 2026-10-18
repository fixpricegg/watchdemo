import { useEffect, useRef, useState } from "react";

function useActiveScrollStep() {
    const containerRef = useRef(null);
    const [activeStep, setActiveStep] = useState(0);

    useEffect(() => {
        const steps = Array.from(containerRef.current?.querySelectorAll("[data-scroll-step]") ?? []);
        if (!steps.length || !window.IntersectionObserver) return undefined;

        const observer = new IntersectionObserver(() => {
            const focusLine = window.innerHeight * 0.46;
            let closestIndex = 0;
            let closestDistance = Infinity;

            steps.forEach((step, index) => {
                const rect = step.getBoundingClientRect();
                const distance = Math.abs(rect.top + rect.height / 2 - focusLine);
                if (distance < closestDistance) {
                    closestIndex = index;
                    closestDistance = distance;
                }
            });

            setActiveStep(closestIndex);
        }, { rootMargin: "-32% 0px -42% 0px", threshold: 0 });

        steps.forEach((step) => observer.observe(step));
        return () => observer.disconnect();
    }, []);

    return { containerRef, activeStep, setActiveStep };
}

export default useActiveScrollStep;
