import { LandingNavbar } from "./components/landing/LandingNavbar";
import { HeroSection } from "./components/landing/HeroSection";
import { ProtocolMarquee } from "./components/landing/ProtocolMarquee";
import { BentoFeatures } from "./components/landing/BentoFeatures";
import { ThreatSandbox } from "./components/landing/ThreatSandbox";
import { LandingFooter } from "./components/landing/LandingFooter";

interface LandingPageProps {
  onLaunchDashboard: () => void;
}

export function LandingPage({ onLaunchDashboard }: LandingPageProps) {
  return (
    <div className="landing-wrapper">
      <LandingNavbar onLaunchDashboard={onLaunchDashboard} />
      <HeroSection onLaunchDashboard={onLaunchDashboard} />
      <ProtocolMarquee />
      <BentoFeatures />
      <ThreatSandbox />
      <LandingFooter />
    </div>
  );
}
