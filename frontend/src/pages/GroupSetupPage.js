import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { createGroup } from '@/utils/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Sparkles, ArrowLeft, Copy, Check, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const GroupSetupPage = () => {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [inviteCode, setInviteCode] = useState('');
  const [groupId, setGroupId] = useState('');
  const [step, setStep] = useState(1);
  const [members, setMembers] = useState([]);
  const [fetchingMembers, setFetchingMembers] = useState(false);

  const [minStartTime, setMinStartTime] = useState("00:00");
  const [minEndTime, setMinEndTime] = useState("00:00");

  const today = new Date().toISOString().split('T')[0];

  const [formData, setFormData] = useState({
    name: '',
    event_date: today,
    start_time: '',
    end_time: '',
    indoor_outdoor: 'both',
    budget_range: 'medium',
    ott_subscriptions: [],
    board_games: []
  });

  const getCurrentTime = () => {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
  };

  useEffect(() => {
    const nowTime = getCurrentTime();
    setMinStartTime(nowTime);
    setMinEndTime(nowTime);
  }, []);

  const ottOptions = ['Netflix', 'Prime Video', 'Disney+', 'HBO Max', 'Hulu'];
  const gamesOptions = ['Chess', 'Monopoly', 'Scrabble', 'Cards', 'Jenga'];

  const handleDateChange = (e) => {
    const newDate = e.target.value;
    setFormData({ ...formData, event_date: newDate });

    const nowTime = getCurrentTime();

    if (newDate === today) {
      setMinStartTime(nowTime);
      setMinEndTime(nowTime);
    } else {
      setMinStartTime("00:00");
      setMinEndTime("00:00");
    }

    setFormData(prev => ({ ...prev, start_time: '', end_time: '' }));
  };

  const handleStartTimeChange = (e) => {
    const newTime = e.target.value;
    setFormData({ ...formData, start_time: newTime });
    setMinEndTime(newTime);
  };

  useEffect(() => {
    let interval;
    if (step === 2 && groupId) {
      const fetchMembers = async () => {
        setFetchingMembers(true);
        try {
          const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/groups/${groupId}`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          setMembers(response.data.members);
        } catch (e) {
          console.error(e);
        } finally {
          setFetchingMembers(false);
        }
      };

      fetchMembers();
      interval = setInterval(fetchMembers, 3000);
    }
    return () => clearInterval(interval);
  }, [step, groupId, token]);

  const handleCreate = async () => {
    if (!formData.start_time || !formData.end_time) {
      toast.error("Please select start and end times.");
      return;
    }

    if (formData.event_date === today && formData.start_time < minStartTime) {
      toast.error("Start time cannot be in the past for today.");
      return;
    }

    if (formData.end_time <= formData.start_time) {
      toast.error("End time must be after start time.");
      return;
    }

    setLoading(true);
    try {
      const response = await createGroup(formData, token);
      setInviteCode(response.data.invite_code);
      setGroupId(response.data.id);
      setMembers(response.data.members);
      setStep(2);
      toast.success('Group created! Share code to invite.');
    } catch (error) {
      toast.error('Failed to create group');
    } finally {
      setLoading(false);
    }
  };

  const copyInviteCode = () => {
    navigator.clipboard.writeText(inviteCode);
    setCopiedCode(true);
    toast.success('Invite code copied!');
    setTimeout(() => setCopiedCode(false), 2000);
  };

  if (step === 2) {
    const isAlone = members.length <= 1;

    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex items-center justify-center p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-2xl"
        >
          <Card className="glass border-2">
            <CardHeader className="text-center">
              <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                <Sparkles className="w-10 h-10 text-primary" />
              </div>
              <CardTitle className="text-3xl font-outfit font-bold">Group Lobby</CardTitle>
              <CardDescription className="text-base">Waiting for members to join...</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="bg-primary/5 rounded-2xl p-8 text-center">
                <Label className="text-sm text-muted-foreground mb-2 block">Invite Code</Label>
                <div className="text-5xl font-mono font-bold tracking-widest text-primary mb-4" data-testid="invite-code-display">
                  {inviteCode}
                </div>
                <Button
                  variant="outline"
                  onClick={copyInviteCode}
                  className="rounded-full"
                  data-testid="copy-invite-code-btn"
                >
                  {copiedCode ? (
                    <><Check className="w-4 h-4 mr-2" /> Copied!</>
                  ) : (
                    <><Copy className="w-4 h-4 mr-2" /> Copy Code</>
                  )}
                </Button>
              </div>

              <div className="space-y-3">
                <p className="text-center text-muted-foreground">
                  Once everyone is here, continue to preferences.
                </p>
                <div className="space-y-2">
                  <h3 className="font-semibold text-center">Joined Members ({members.length})</h3>
                  <div className="max-h-40 overflow-y-auto space-y-2">
                    {members.map((m, i) => (
                      <div key={i} className="flex items-center justify-between p-3 glass rounded-lg">
                        <span className="capitalize">{m.role} {i + 1}</span>
                        <CheckCircle2 className="w-4 h-4 text-primary" />
                      </div>
                    ))}
                    {fetchingMembers && <Loader2 className="w-4 h-4 animate-spin mx-auto" />}
                  </div>
                </div>
                <Button
                  className="w-full rounded-full shadow-lg shadow-primary/20"
                  size="lg"
                  onClick={() => navigate(`/group/${groupId}/survey`)}
                  disabled={isAlone}
                  data-testid="continue-to-survey-btn"
                >
                  {isAlone ? "Wait for at least 1 more person" : "Everyone is here! Continue to Preferences"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 p-6">
      <div className="max-w-3xl mx-auto py-8">
        <Button
          variant="ghost"
          onClick={() => navigate('/dashboard')}
          className="mb-6"
          data-testid="back-to-dashboard-btn"
        >
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Dashboard
        </Button>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="glass border-2">
            <CardHeader>
              <CardTitle className="text-3xl font-outfit font-bold">Group Setup</CardTitle>
              <CardDescription className="text-base">
                Tell us about your group's plan
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={(e) => { e.preventDefault(); handleCreate(); }} className="space-y-8">

                {/* Group Name */}
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-base font-medium">Group Name</Label>
                  <Input
                    id="name"
                    placeholder="Weekend Squad"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    className="text-lg h-12"
                    data-testid="group-name-input"
                  />
                </div>

                {/* Date & Time Section */}
                <div className="space-y-4">
                  <Label className="text-base font-medium">When are you free?</Label>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Date Picker */}
                    <div className="space-y-2">
                      <Label htmlFor="date" className="text-sm text-muted-foreground">Date</Label>
                      <Input
                        id="date"
                        type="date"
                        min={today}
                        value={formData.event_date}
                        onChange={handleDateChange}
                        required
                        className="text-base h-12"
                        data-testid="event-date-input"
                      />
                    </div>

                    {/* Start Time */}
                    <div className="space-y-2">
                      <Label htmlFor="start_time" className="text-sm text-muted-foreground">Start</Label>
                      <Input
                        id="start_time"
                        type="time"
                        min={minStartTime}
                        value={formData.start_time}
                        onChange={handleStartTimeChange}
                        required
                        className="text-base h-12"
                        data-testid="start-time-input"
                      />
                    </div>

                    {/* End Time */}
                    <div className="space-y-2">
                      <Label htmlFor="end_time" className="text-sm text-muted-foreground">End</Label>
                      <Input
                        id="end_time"
                        type="time"
                        min={minEndTime}
                        value={formData.end_time}
                        onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                        required
                        className="text-base h-12"
                        data-testid="end-time-input"
                      />
                    </div>
                  </div>
                </div>

                {/* Activity Type */}
                <div className="space-y-2">
                  <Label htmlFor="indoor-outdoor" className="text-base font-medium">Activity Type</Label>
                  <Select value={formData.indoor_outdoor} onValueChange={(value) => setFormData({ ...formData, indoor_outdoor: value })}>
                    <SelectTrigger className="text-lg h-12" data-testid="indoor-outdoor-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="indoor">Indoor Only</SelectItem>
                      <SelectItem value="outdoor">Outdoor Only</SelectItem>
                      <SelectItem value="both">Both Indoor & Outdoor</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Budget in Rupees */}
                <div className="space-y-2">
                  <Label htmlFor="budget" className="text-base font-medium">Budget Range (₹)</Label>
                  <Select value={formData.budget_range} onValueChange={(value) => setFormData({ ...formData, budget_range: value })}>
                    <SelectTrigger className="text-lg h-12" data-testid="budget-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="free">Free (₹0)</SelectItem>
                      <SelectItem value="low">Low (₹1 - ₹500)</SelectItem>
                      <SelectItem value="medium">Medium (₹500 - ₹2000)</SelectItem>
                      <SelectItem value="high">High (₹2000+)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* OTT Subscriptions (Conditional) */}
                {(formData.indoor_outdoor === 'indoor' || formData.indoor_outdoor === 'both') && (
                  <div className="space-y-3">
                    <Label className="text-base font-medium">Available Streaming Services</Label>
                    <div className="grid grid-cols-2 gap-3">
                      {ottOptions.map((ott) => (
                        <div key={ott} className="flex items-center space-x-2">
                          <Checkbox
                            id={ott}
                            checked={formData.ott_subscriptions.includes(ott)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setFormData({ ...formData, ott_subscriptions: [...formData.ott_subscriptions, ott] });
                              } else {
                                setFormData({ ...formData, ott_subscriptions: formData.ott_subscriptions.filter(o => o !== ott) });
                              }
                            }}
                            data-testid={`ott-${ott.toLowerCase().replace(/\s+/g, '-')}`}
                          />
                          <Label htmlFor={ott} className="cursor-pointer">{ott}</Label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <Button
                  type="submit"
                  className="w-full rounded-full text-lg h-12 shadow-lg shadow-primary/20"
                  disabled={loading}
                  data-testid="create-group-submit-btn"
                >
                  {loading ? 'Creating Group...' : 'Create Group'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default GroupSetupPage;