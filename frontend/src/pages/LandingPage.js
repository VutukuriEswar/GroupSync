import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, Link } from 'react-router-dom';
import { Sparkles, Users, Brain, Shield, ArrowRight, CheckCircle2, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';

const LandingPage = () => {
  const navigate = useNavigate();
  const [showAuth, setShowAuth] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="relative overflow-hidden"
      >
        <header className="glass sticky top-0 z-50 px-6 py-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-8 h-8 text-primary" />
              <span className="text-2xl font-outfit font-bold">GroupSync</span>
            </div>
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                onClick={() => navigate('/login')}
                data-testid="header-login-btn"
              >
                Login
              </Button>
              <Button
                onClick={() => navigate('/register')}
                className="rounded-full shadow-lg shadow-primary/20"
                data-testid="header-register-btn"
              >
                Get Started
              </Button>
            </div>
          </div>
        </header>

        <div className="max-w-7xl mx-auto px-6 py-24">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <h1 className="text-5xl sm:text-6xl lg:text-7xl font-outfit font-black tracking-tight leading-tight mb-6">
                Stop Arguing,
                <br />
                <span className="text-gradient">Start Enjoying</span>
              </h1>
              <p className="text-lg sm:text-xl text-muted-foreground leading-relaxed mb-8">
                AI-powered activity planning for groups. Anonymous, smart, and built for everyone's happiness—not just one person's choice.
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Button
                  size="lg"
                  onClick={() => navigate('/dashboard')}
                  className="rounded-full text-lg px-8 shadow-lg shadow-primary/30 hover:scale-105 transition-transform"
                  data-testid="hero-create-group-btn"
                >
                  Create or Join a Group <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="relative"
            >
              <div className="relative rounded-3xl overflow-hidden shadow-2xl">
                <img
                  src="https://images.pexels.com/photos/3184177/pexels-photo-3184177.jpeg"
                  alt="Group of friends enjoying activities"
                  className="w-full h-auto"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-primary/40 to-transparent"></div>
              </div>
            </motion.div>
          </div>
        </div>
      </motion.div>

      <div className="max-w-7xl mx-auto px-6 py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl sm:text-5xl font-outfit font-bold mb-6">
            How It Works
          </h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            Four simple steps to perfect group plans
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {[
            {
              icon: Users,
              title: "Create Group",
              description: "Set up your group and invite friends with a simple code. No accounts required.",
              color: "text-primary"
            },
            {
              icon: CheckCircle2,
              title: "Share Preferences",
              description: "Everyone answers quick questions about their mood, budget, and interests.",
              color: "text-secondary"
            },
            {
              icon: Brain,
              title: "AI Recommends",
              description: "Our RL engine creates the perfect schedule that makes everyone happy.",
              color: "text-accent"
            },
            {
              icon: Zap,
              title: "Adjust & Enjoy",
              description: "Tweak the plan in real-time. The AI learns from every change.",
              color: "text-primary"
            }
          ].map((feature, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: idx * 0.1 }}
              viewport={{ once: true }}
              whileHover={{ y: -8, transition: { duration: 0.2 } }}
              className="glass rounded-3xl p-8 hover:shadow-xl transition-all"
              data-testid={`feature-card-${idx}`}
            >
              <feature.icon className={`w-12 h-12 ${feature.color} mb-4`} />
              <h3 className="text-xl font-outfit font-bold mb-3">{feature.title}</h3>
              <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-24">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="glass rounded-3xl p-12 lg:p-16"
        >
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <Shield className="w-16 h-16 text-primary mb-6" />
              <h2 className="text-4xl font-outfit font-bold mb-6">
                Privacy First, Always
              </h2>
              <p className="text-lg text-muted-foreground leading-relaxed mb-6">
                We don't track you. We don't sell your data. We learn from group satisfaction, not individual profiles.
              </p>
              <ul className="space-y-4">
                {[
                  "Anonymous session-based learning",
                  "No personal data storage",
                  "Guest users welcome",
                  "Group-level optimization only"
                ].map((item, idx) => (
                  <li key={idx} className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0" />
                    <span className="text-foreground">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="relative">
              <img
                src="https://images.pexels.com/photos/7348940/pexels-photo-7348940.jpeg"
                alt="Friends hiking outdoors"
                className="rounded-2xl shadow-2xl"
              />
            </div>
          </div>
        </motion.div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="glass rounded-3xl p-12 lg:p-16 text-center"
        >
          <h2 className="text-4xl sm:text-5xl font-outfit font-bold mb-6">
            Ready to Plan Better?
          </h2>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Join thousands making group decisions easier, fairer, and more fun.
          </p>
          <Button
            size="lg"
            onClick={() => navigate('/dashboard')}
            className="rounded-full text-lg px-12 shadow-lg shadow-primary/30 hover:scale-105 transition-transform"
            data-testid="cta-get-started-btn"
          >
            Get Started Free <Sparkles className="ml-2 w-5 h-5" />
          </Button>
        </motion.div>
      </div>
    </div>
  );
};

export default LandingPage;