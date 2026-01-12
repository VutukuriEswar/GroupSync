import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { register as registerApi, login as loginApi } from '@/utils/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Sparkles, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

const RegisterPage = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: ''
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await registerApi(formData);
      const loginResponse = await loginApi({ email: formData.email, password: formData.password });
      login(loginResponse.data.token, loginResponse.data.user);
      toast.success('Account created successfully!');
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Button
          variant="ghost"
          onClick={() => navigate('/')}
          className="mb-6"
          data-testid="back-to-home-btn"
        >
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Home
        </Button>

        <Card className="glass border-2">
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <Sparkles className="w-12 h-12 text-primary" />
            </div>
            <CardTitle className="text-3xl font-outfit font-bold">Create Account</CardTitle>
            <CardDescription className="text-base">Join the smarter way to plan group activities</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name" className="text-base font-medium">Name</Label>
                <Input
                  id="name"
                  type="text"
                  placeholder="Your name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  className="text-lg h-12"
                  data-testid="register-name-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="text-base font-medium">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                  className="text-lg h-12"
                  data-testid="register-email-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-base font-medium">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  minLength={6}
                  className="text-lg h-12"
                  data-testid="register-password-input"
                />
              </div>

              <Button
                type="submit"
                className="w-full rounded-full text-lg h-12 shadow-lg shadow-primary/20"
                disabled={loading}
                data-testid="register-submit-btn"
              >
                {loading ? 'Creating Account...' : 'Sign Up'}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-muted-foreground">
                Already have an account?{' '}
                <Link to="/login" className="text-primary hover:underline font-medium" data-testid="go-to-login-link">
                  Login
                </Link>
              </p>
              <p className="mt-4 text-sm text-muted-foreground">
                Or{' '}
                <Link to="/dashboard" className="text-primary hover:underline font-medium" data-testid="continue-as-guest-link">
                  continue as guest
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export default RegisterPage;