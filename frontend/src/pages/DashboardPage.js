import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Sparkles, Plus, Users, LogOut, User } from 'lucide-react';
import { toast } from 'sonner';
import { joinGroup } from '@/utils/api';

const DashboardPage = () => {
  const navigate = useNavigate();
  const { user, isGuest, logout } = useAuth();
  const [inviteCode, setInviteCode] = useState('');
  const [joining, setJoining] = useState(false);

  const handleJoinGroup = async () => {
    if (!inviteCode.trim()) {
      toast.error('Please enter an invite code');
      return;
    }

    setJoining(true);
    try {
      const token = localStorage.getItem('token');
      const response = await joinGroup(inviteCode.toUpperCase(), token);
      toast.success('Joined group successfully!');
      navigate(`/group/${response.data.group_id}/survey`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to join group');
    } finally {
      setJoining(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      {/* Header */}
      <header className="glass sticky top-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-8 h-8 text-primary" />
            <span className="text-2xl font-outfit font-bold">GroupSync</span>
          </div>
          <div className="flex items-center gap-4">
            {!isGuest() && (
              <div className="flex items-center gap-2 text-sm" data-testid="user-info">
                <User className="w-4 h-4" />
                <span>{user?.name}</span>
              </div>
            )}
            {isGuest() ? (
              <Button variant="outline" onClick={() => navigate('/login')} data-testid="login-btn">
                Login
              </Button>
            ) : (
              <Button variant="ghost" onClick={logout} data-testid="logout-btn">
                <LogOut className="w-4 h-4 mr-2" /> Logout
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-5xl mx-auto px-6 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="text-center mb-16">
            <h1 className="text-5xl font-outfit font-black mb-4">
              {isGuest() ? 'Welcome, Guest!' : `Welcome, ${user?.name}!`}
            </h1>
            <p className="text-xl text-muted-foreground">
              Create a new group or join an existing one to get started
            </p>
          </div>

          {/* Action Cards */}
          <div className="grid md:grid-cols-2 gap-8">
            {/* Create Group Card */}
            <motion.div
              whileHover={{ y: -8 }}
              transition={{ duration: 0.2 }}
            >
              <Card className="glass h-full hover:shadow-xl transition-shadow cursor-pointer border-2" onClick={() => navigate('/group/create')} data-testid="create-group-card">
                <CardHeader>
                  <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                    <Plus className="w-8 h-8 text-primary" />
                  </div>
                  <CardTitle className="text-2xl font-outfit font-bold">Create New Group</CardTitle>
                  <CardDescription className="text-base">
                    Start a new activity planning session and invite your friends
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button className="w-full rounded-full shadow-lg shadow-primary/20" size="lg" data-testid="create-group-btn">
                    Create Group
                  </Button>
                </CardContent>
              </Card>
            </motion.div>

            {/* Join Group Card */}
            <motion.div
              whileHover={{ y: -8 }}
              transition={{ duration: 0.2 }}
            >
              <Card className="glass h-full hover:shadow-xl transition-shadow border-2" data-testid="join-group-card">
                <CardHeader>
                  <div className="w-16 h-16 rounded-full bg-secondary/10 flex items-center justify-center mb-4">
                    <Users className="w-8 h-8 text-primary" />
                  </div>
                  <CardTitle className="text-2xl font-outfit font-bold">Join Group</CardTitle>
                  <CardDescription className="text-base">
                    Have an invite code? Join your friends' activity planning session
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Input
                    placeholder="Enter invite code"
                    value={inviteCode}
                    onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                    className="text-lg h-12 text-center font-mono tracking-widest"
                    maxLength={8}
                    data-testid="invite-code-input"
                  />
                  <Button
                    className="w-full rounded-full shadow-lg shadow-primary/20"
                    size="lg"
                    onClick={handleJoinGroup}
                    disabled={joining}
                    data-testid="join-group-btn"
                  >
                    {joining ? 'Joining...' : 'Join Group'}
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Guest Notice */}
          {isGuest() && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mt-12 text-center"
            >
              <Card className="glass max-w-2xl mx-auto">
                <CardContent className="pt-6">
                  <p className="text-muted-foreground mb-4">
                    <strong>Tip:</strong> Create an account to save your preferences and access more detailed recommendations!
                  </p>
                  <Button variant="outline" onClick={() => navigate('/register')} data-testid="register-prompt-btn">
                    Create Free Account
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default DashboardPage;