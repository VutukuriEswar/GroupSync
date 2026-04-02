import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Sparkles, Plus, Users, LogOut, User, RotateCcw, Clock, Trash2, Edit, UserX, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { joinGroup, getMyGroups, restartGroup } from '@/utils/api';
import axios from 'axios';

const DashboardPage = () => {
  const navigate = useNavigate();
  const { user, isGuest, logout } = useAuth();
  const [inviteCode, setInviteCode] = useState('');
  const [myGroups, setMyGroups] = useState([]);
  const [loadingGroups, setLoadingGroups] = useState(true);

  useEffect(() => {
    if (!isGuest()) fetchGroups();
  }, [isGuest]);

  const fetchGroups = async () => {
    setLoadingGroups(true);
    try {
      const response = await getMyGroups();
      setMyGroups(response.data.groups);
    } catch (error) {
      console.error(error);
    } finally {
      setLoadingGroups(false);
    }
  };

  const isGroupTimeValid = (group) => {
    const constraints = group.constraints || {};
    const startStr = constraints.start_date + ' ' + constraints.start_time;
    try {
      return new Date(startStr) > new Date();
    } catch {
      return true;
    }
  };

  const handleJoinGroup = async () => {
    if (!inviteCode.trim()) {
      toast.error('Please enter an invite code');
      return;
    }
    try {
      const token = localStorage.getItem('token');
      const response = await joinGroup(inviteCode.toUpperCase(), token);
      if (response.data.member_id) {
        localStorage.setItem('current_member_id', response.data.member_id);
      }
      toast.success('Joined group successfully!');
      navigate(`/group/${response.data.group_id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to join group');
    }
  };

  const handleGroupClick = (group) => {
    if (!isGroupTimeValid(group) && group.status !== 'completed') {
      toast.error("Event time has passed. Please edit timings.");
    }
    navigate(`/group/${group.id}`);
  };

  const handleEditGroup = (groupId, e) => {
    e.stopPropagation();
    navigate(`/group/${groupId}/edit`);
  };

  const handleRestartGroup = async (groupId, e) => {
    e.stopPropagation();
    try {
      await restartGroup(groupId);
      toast.success("Group restarted!");
      navigate(`/group/${groupId}`);
    } catch (error) {
      toast.error("Failed to restart group");
    }
  };

  const handleQuitGroup = async (groupId, e) => {
    e.stopPropagation();
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${process.env.REACT_APP_BACKEND_URL}/api/groups/${groupId}/quit`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success("You have left the group");
      fetchGroups();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to quit group");
    }
  };

  const handleDeleteGroup = async (groupId, e) => {
    e.stopPropagation();
    if (!window.confirm("Delete this group permanently?")) return;
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${process.env.REACT_APP_BACKEND_URL}/api/groups/${groupId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success("Group deleted");
      fetchGroups();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed");
    }
  };

  const handleSoloPlan = () => {
    navigate('/group/create', { state: { isSolo: true } });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      <header className="glass sticky top-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-8 h-8 text-primary" />
            <span className="text-2xl font-outfit font-bold">GroupSync</span>
          </div>
          <div className="flex items-center gap-4">
            {!isGuest() && (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 text-sm">
                  <User className="w-4 h-4" />
                  <span>{user?.name}</span>
                </div>
                <Button variant="outline" size="sm" onClick={() => navigate('/profile')}>
                  Profile
                </Button>
              </div>
            )}
            {isGuest() ? (
              <Button variant="outline" onClick={() => navigate('/login')}>
                Login
              </Button>
            ) : (
              <Button variant="ghost" onClick={logout}>
                <LogOut className="w-4 h-4 mr-2" /> Logout
              </Button>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <div className="text-center mb-12">
            <h1 className="text-5xl font-outfit font-black mb-4">
              {isGuest() ? 'Welcome, Guest!' : `Welcome, ${user?.name}!`}
            </h1>
            <p className="text-xl text-muted-foreground">
              Create a new group, join one, or plan a solo trip!
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 mb-16">
            <motion.div whileHover={{ y: -8 }} transition={{ duration: 0.2 }}>
              <Card className="glass h-full hover:shadow-xl transition-shadow cursor-pointer border-2" onClick={() => navigate('/group/create')}>
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center">
                    <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                      <Plus className="w-8 h-8 text-primary" />
                    </div>
                    <h3 className="text-xl font-bold mb-2">Create Group</h3>
                    <p className="text-muted-foreground text-center text-sm">Start planning with friends</p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div whileHover={{ y: -8 }} transition={{ duration: 0.2 }}>
              <Card className="glass h-full hover:shadow-xl transition-shadow cursor-pointer border-2 border-secondary" onClick={handleSoloPlan}>
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center">
                    <div className="w-16 h-16 rounded-full bg-secondary/10 flex items-center justify-center mb-4">
                      <User className="w-8 h-8 text-secondary" />
                    </div>
                    <h3 className="text-xl font-bold mb-2">Solo Plan</h3>
                    <p className="text-muted-foreground text-center text-sm">Just for you</p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div whileHover={{ y: -8 }} transition={{ duration: 0.2 }}>
              <Card className="glass h-full hover:shadow-xl transition-shadow border-2">
                <CardContent className="pt-6 space-y-4">
                  <div className="flex flex-col items-center">
                    <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mb-4">
                      <Users className="w-8 h-8 text-accent" />
                    </div>
                    <h3 className="text-xl font-bold mb-2">Join Group</h3>
                    <p className="text-muted-foreground text-center mb-4">Have an invite code?</p>
                  </div>
                  <Input
                    placeholder="Enter invite code"
                    value={inviteCode}
                    onChange={(e) => setInviteCode(e.target.value.toUpperCase())}
                    className="text-lg h-12 text-center font-mono tracking-widest"
                    maxLength={8}
                  />
                  <Button className="w-full rounded-full" size="lg" onClick={handleJoinGroup}>
                    Join Group
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {!isGuest() && !loadingGroups && myGroups.length > 0 && (
            <div className="space-y-6">
              <h2 className="text-3xl font-outfit font-bold">My Groups</h2>
              <div className="grid gap-4">
                {myGroups.map((group) => {
                  const isCreator = group.creator_id === user?.id;
                  const isPast = !isGroupTimeValid(group) && group.status !== 'completed';

                  return (
                    <Card
                      key={group.id}
                      className={`glass hover:border-primary/50 transition-colors cursor-pointer ${isPast ? 'border-red-200 bg-red-50/30' : ''}`}
                      onClick={() => handleGroupClick(group)}
                    >
                      <CardContent className="p-6">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <h3 className="text-xl font-bold">{group.name}</h3>
                              {isPast && (
                                <span className="flex items-center gap-1 text-xs text-red-500 font-semibold">
                                  <AlertCircle className="w-3 h-3" /> Time Passed
                                </span>
                              )}
                              <span className={`px-2 py-1 rounded-full text-xs font-semibold ${group.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                                {group.status}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-sm text-muted-foreground">
                              <div className="flex items-center gap-1">
                                <Users className="w-4 h-4" />
                                {group.members.length} Members
                              </div>
                              <div className="flex items-center gap-1">
                                <Clock className="w-4 h-4" />
                                {group.constraints?.schedule_display}
                              </div>
                            </div>
                          </div>

                          <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                            {isCreator ? (
                              <>
                                {group.status === 'completed' && (
                                  <Button variant="outline" size="sm" onClick={(e) => handleRestartGroup(group.id, e)}>
                                    <RotateCcw className="w-4 h-4 mr-2" /> Replay
                                  </Button>
                                )}
                                <Button variant="outline" size="sm" onClick={(e) => handleEditGroup(group.id, e)}>
                                  <Edit className="w-4 h-4 mr-2" /> Edit
                                </Button>
                                <Button variant="destructive" size="sm" onClick={(e) => handleDeleteGroup(group.id, e)}>
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </>
                            ) : (
                              <Button variant="outline" size="sm" onClick={(e) => handleQuitGroup(group.id, e)}>
                                <UserX className="w-4 h-4 mr-2" /> Quit
                              </Button>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default DashboardPage;