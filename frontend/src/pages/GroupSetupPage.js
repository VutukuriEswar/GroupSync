import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { createGroup } from '@/utils/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Sparkles, ArrowLeft, Copy, Check, Loader2, CircleCheck, MapPin, UserX, Navigation } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const GroupSetupPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { token, user } = useAuth();
  const { groupId: urlGroupId } = useParams();

  const isSoloPlan = location.state?.isSolo || false;

  const [loading, setLoading] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);
  const [inviteCode, setInviteCode] = useState('');
  const [groupId, setGroupId] = useState('');
  const [step, setStep] = useState(1);
  const [members, setMembers] = useState([]);
  const [fetchingMembers, setFetchingMembers] = useState(false);

  const [iCreatedThisGroup, setICreatedThisGroup] = useState(false);
  const [creatorId, setCreatorId] = useState('');
  const [groupStatus, setGroupStatus] = useState('lobby');

  const [myLocation, setMyLocation] = useState(null);
  const [updatingLocation, setUpdatingLocation] = useState(false);

  const [hasMeetingPlace, setHasMeetingPlace] = useState(false);

  const [minStartTime, setMinStartTime] = useState("00:00");
  const [minEndTime, setMinEndTime] = useState("00:00");

  const today = new Date().toISOString().split('T')[0];

  const [formData, setFormData] = useState({
    name: '',
    event_date: today,
    end_date: today,
    start_time: '',
    end_time: '',
    indoor_outdoor: 'both',
    budget_range: 'medium',
    ott_subscriptions: [],
    board_games: [],
    is_vacation: false,
    vacation_days: 1,
    destination_choice: '',

    meeting_place: ''
  });

  const popularAreas = [
    'MG Road', 'Benz Circle', 'Governorpet', 'Moghalrajpuram',
    'Labbipet', 'Suryaraopet', 'One Town', 'Ramarao Peta',
    'Gunadala', 'Patamata', 'Autonagar', 'Bundar Road',
    'Eluru Road', 'Kanyakaparameswari Temple Area', 'Prakasam Barrage'
  ];

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
    setFormData({ ...formData, event_date: newDate, end_date: newDate });
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
    if (urlGroupId) {
      setGroupId(urlGroupId);
      setStep(2);

      const myCreatedGroup = localStorage.getItem('createdGroupId');
      if (myCreatedGroup === urlGroupId) {
        setICreatedThisGroup(true);
      }
    }
  }, [urlGroupId]);

  useEffect(() => {
    let interval;
    if (step === 2 && groupId) {
      const fetchGroupStatus = async () => {
        setFetchingMembers(true);
        try {
          const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/groups/${groupId}/members`, {
            headers: { Authorization: `Bearer ${token}` }
          });

          setMembers(response.data.members);

          const groupRes = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/groups/${groupId}`, {
            headers: { Authorization: `Bearer ${token}` }
          });

          setCreatorId(groupRes.data.creator_id);
          setGroupStatus(groupRes.data.status);
          setInviteCode(groupRes.data.invite_code);

          if (groupRes.data.constraints) {
            setFormData(prev => ({
              ...prev,
              is_vacation: groupRes.data.constraints.is_vacation || false,
              destination_choice: groupRes.data.constraints.destination_choice || '',
              meeting_place: groupRes.data.constraints.meeting_place || ''
            }));

            if (groupRes.data.constraints.meeting_place) {
              setHasMeetingPlace(true);
            }
          }

          if (groupRes.data.status === 'preferences') {
            navigate(`/group/${groupId}/survey`);
          }

        } catch (e) {
          console.error(e);
        } finally {
          setFetchingMembers(false);
        }
      };

      fetchGroupStatus();
      interval = setInterval(fetchGroupStatus, 3000);
    }
    return () => clearInterval(interval);
  }, [step, groupId, token, navigate]);

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
      const payload = {
        name: isSoloPlan ? "Solo Plan" : formData.name,
        start_date: formData.event_date,
        end_date: formData.end_date || formData.event_date,
        start_time: formData.start_time,
        end_time: formData.end_time,
        indoor_outdoor: formData.indoor_outdoor,
        budget_range: formData.budget_range,
        ott_subscriptions: formData.ott_subscriptions,
        board_games: formData.board_games,
        is_vacation: formData.is_vacation,
        vacation_days: formData.vacation_days,
        destination_choice: formData.destination_choice,

        meeting_place: formData.meeting_place || null
      };

      const response = await createGroup(payload, token);
      const newGroupId = response.data.id;
      const myMemberId = response.data.creator_id || response.data.members?.[0]?.id;

      if (myMemberId) {
        localStorage.setItem('current_member_id', myMemberId);
      }
      localStorage.setItem('createdGroupId', newGroupId);

      if (formData.meeting_place) {
        setHasMeetingPlace(true);
      }

      if (isSoloPlan) {

        try {
          const config = { headers: {} };
          const body = {};
          if (token) config.headers['Authorization'] = `Bearer ${token}`;
          else body.user_id = myMemberId;

          await axios.post(
            `${process.env.REACT_APP_BACKEND_URL}/api/groups/${newGroupId}/start`,
            body,
            config
          );

          toast.success('Solo plan created! Starting survey...');
          navigate(`/group/${newGroupId}/survey`);
        } catch (startError) {
          console.error(startError);
          toast.error("Failed to start solo session");
          navigate(`/group/${newGroupId}`);
        }
      } else {
        setInviteCode(response.data.invite_code);
        setGroupId(newGroupId);
        setCreatorId(myMemberId);
        setMembers(response.data.members);
        setStep(2);
        setICreatedThisGroup(true);
        toast.success('Group created! Share code to invite.');
      }
    } catch (error) {
      toast.error('Failed to create group');
    } finally {
      setLoading(false);
    }
  };

  const handleStartSession = async () => {
    try {
      const config = { headers: {} };
      const body = {};

      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
      } else {
        body.user_id = creatorId;
      }

      await axios.post(
        `${process.env.REACT_APP_BACKEND_URL}/api/groups/${groupId}/start`,
        body,
        config
      );

      toast.success("Starting session...");
    } catch (error) {
      console.error(error);
      toast.error("Failed to start session");
    }
  };

  const handleRemoveMember = async (memberId) => {
    if (!window.confirm("Remove this member from the group?")) return;
    try {
      await axios.delete(`${process.env.REACT_APP_BACKEND_URL}/api/groups/${groupId}/members/${memberId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success("Member removed");
      setMembers(prev => prev.filter(m => m.id !== memberId));
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to remove");
    }
  };

  const handleGetLocation = async () => {
    if (!navigator.geolocation) {
      toast.error("Geolocation is not supported by your browser");
      return;
    }

    setUpdatingLocation(true);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        const newLoc = { lat: latitude, lon: longitude };

        setMyLocation(newLoc);

        const updateBackend = async () => {
          try {
            const payload = { ...newLoc };
            const headers = {};

            if (token) {
              headers['Authorization'] = `Bearer ${token}`;
            } else {
              const storedId = localStorage.getItem('current_member_id');
              if (storedId) {
                payload.user_id = storedId;
              } else {
                toast.error("We couldn't identify you. Please refresh.");
                setUpdatingLocation(false);
                return;
              }
            }

            await axios.post(
              `${process.env.REACT_APP_BACKEND_URL}/api/groups/${groupId}/location`,
              payload,
              { headers }
            );
            toast.success("Location saved!");
          } catch (err) {
            console.error(err);
            toast.error("Failed to save location");
          } finally {
            setUpdatingLocation(false);
          }
        };

        updateBackend();
      },
      (error) => {
        setUpdatingLocation(false);
        toast.error("Unable to retrieve your location. Please allow access.");
      }
    );
  };

  const copyInviteCode = () => {
    navigator.clipboard.writeText(inviteCode);
    setCopiedCode(true);
    toast.success('Invite code copied!');
    setTimeout(() => setCopiedCode(false), 2000);
  };

  if (step === 2) {
    const isAlone = members.length <= 1;
    const isCreator = iCreatedThisGroup || (user && (user.id === creatorId || user.user_id === creatorId));

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

              {hasMeetingPlace && formData.meeting_place && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-3">
                  <Navigation className="w-5 h-5 text-green-600" />
                  <div>
                    <p className="font-medium text-green-800">Meeting Place Set</p>
                    <p className="text-sm text-green-600">Everyone will meet at: <strong>{formData.meeting_place}</strong></p>
                  </div>
                </div>
              )}

              <div className="space-y-3">
                <p className="text-center text-muted-foreground">
                  Once everyone is here, creator will continue.
                </p>
                <div className="space-y-2">
                  <h3 className="font-semibold text-center">Joined Members ({members.length})</h3>
                  <div className="max-h-60 overflow-y-auto space-y-2">
                    {members.map((m, i) => {
                      const isMe = (user?.id === m.id || user?.user_id === m.id || localStorage.getItem('current_member_id') === m.id);
                      const hasLoc = m.location && m.location.lat !== 0;

                      return (
                        <div key={i} className="flex items-center justify-between p-3 glass rounded-lg">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center font-semibold text-sm">
                              {m.role === 'creator' ? '👑' : m.name ? m.name.charAt(0).toUpperCase() : '?'}
                            </div>
                            <div>
                              <p className="font-medium">
                                {m.name || 'Loading...'}
                                {isMe && <span className="text-xs text-muted-foreground ml-1">(You)</span>}
                              </p>
                              {hasMeetingPlace ? (
                                <p className="text-xs text-green-600 flex items-center gap-1">
                                  <Navigation className="w-3 h-3" /> Meeting at: {formData.meeting_place}
                                </p>
                              ) : hasLoc ? (
                                <p className="text-xs text-green-600 flex items-center gap-1">
                                  <MapPin className="w-3 h-3" /> Located
                                </p>
                              ) : (
                                <p className="text-xs text-muted-foreground">Location Unknown</p>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {!hasMeetingPlace && isMe ? (
                              updatingLocation ? (
                                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                              ) : myLocation ? (
                                <CircleCheck className="w-4 h-4 text-green-500" />
                              ) : (
                                <Button size="sm" variant="outline" onClick={handleGetLocation} className="text-xs h-8">
                                  <MapPin className="w-3 h-3 mr-1" /> Locate
                                </Button>
                              )
                            ) : null}
                            {isCreator && m.role !== 'creator' && (
                              <Button variant="ghost" size="sm" className="text-red-500 hover:bg-red-50 h-8" onClick={() => handleRemoveMember(m.id)}>
                                <UserX className="w-4 h-4" />
                              </Button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                    {fetchingMembers && <Loader2 className="w-4 h-4 animate-spin mx-auto" />}
                  </div>
                </div>

                {isCreator ? (
                  <Button
                    className="w-full rounded-full shadow-lg shadow-primary/20"
                    size="lg"
                    onClick={handleStartSession}
                    disabled={isAlone}
                    data-testid="continue-to-survey-btn"
                  >
                    {isAlone ? "Wait for at least 1 more person" : "Everyone is here! Continue to Preferences"}
                  </Button>
                ) : (
                  <div className="w-full text-center text-sm text-muted-foreground py-3 bg-muted/30 rounded-lg border border-dashed">
                    Waiting for the creator to start the session...
                  </div>
                )}
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
              <CardTitle className="text-3xl font-outfit font-bold">
                {isSoloPlan ? "Plan Your Solo Trip" : "Group Setup"}
              </CardTitle>
              <CardDescription className="text-base">
                {isSoloPlan ? "Tell us about your preferences" : "Tell us about your group's plan"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={(e) => { e.preventDefault(); handleCreate(); }} className="space-y-8">

                {!isSoloPlan && (
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
                )}

                <div className="space-y-2">
                  <Label htmlFor="meeting_place" className="text-base font-medium">
                    Meeting Place <span className="text-muted-foreground font-normal">(Optional)</span>
                  </Label>
                  <Input
                    id="meeting_place"
                    placeholder="e.g., Moghalrajpuram, MG Road, City Center"
                    value={formData.meeting_place}
                    onChange={(e) => setFormData({ ...formData, meeting_place: e.target.value })}
                    className="text-lg h-12"
                    data-testid="meeting-place-input"
                  />
                  <p className="text-sm text-muted-foreground">
                    If set, recommendations will be centered around this location instead of individual member locations
                  </p>

                  <div className="flex flex-wrap gap-2 mt-2">
                    {popularAreas.slice(0, 8).map((area) => (
                      <button
                        key={area}
                        type="button"
                        onClick={() => setFormData({ ...formData, meeting_place: area })}
                        className={`px-3 py-1 text-xs rounded-full border transition-colors ${formData.meeting_place === area
                          ? 'bg-primary text-white border-primary'
                          : 'bg-muted hover:bg-primary/10 border-muted'
                          }`}
                      >
                        {area}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex items-center space-x-2 p-4 border rounded-lg bg-blue-50/50">
                  <Checkbox
                    id="vacation-mode"
                    checked={formData.is_vacation}
                    onCheckedChange={(checked) => setFormData({ ...formData, is_vacation: checked })}
                  />
                  <div className="grid gap-1.5 leading-none">
                    <label
                      htmlFor="vacation-mode"
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      Vacation Mode
                    </label>
                    <p className="text-xs text-muted-foreground">
                      Plan a multi-day trip itinerary.
                    </p>
                  </div>
                </div>

                {formData.is_vacation && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 border rounded-lg bg-primary/5 animate-in slide-in-from-top-4 duration-300">
                    <div className="space-y-2">
                      <Label htmlFor="vacation_days">Number of Days</Label>
                      <Input
                        id="vacation_days"
                        type="number"
                        min="1"
                        value={formData.vacation_days}
                        onChange={(e) => setFormData({ ...formData, vacation_days: parseInt(e.target.value) })}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="destination">Destination (Optional)</Label>
                      <Input
                        id="destination"
                        placeholder="e.g. Goa, Paris"
                        value={formData.destination_choice}
                        onChange={(e) => setFormData({ ...formData, destination_choice: e.target.value })}
                      />
                    </div>
                  </div>
                )}

                <div className="space-y-4">
                  <Label className="text-base font-medium">When are you free?</Label>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="date" className="text-sm text-muted-foreground">Date</Label>
                      <Input id="date" type="date" min={today} value={formData.event_date} onChange={handleDateChange} required className="text-base h-12" data-testid="event-date-input" />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="start_time" className="text-sm text-muted-foreground">Start</Label>
                      <Input id="start_time" type="time" min={minStartTime} value={formData.start_time} onChange={handleStartTimeChange} required className="text-base h-12" data-testid="start-time-input" />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="end_time" className="text-sm text-muted-foreground">End</Label>
                      <Input id="end_time" type="time" min={minEndTime} value={formData.end_time} onChange={(e) => setFormData({ ...formData, end_time: e.target.value })} required className="text-base h-12" data-testid="end-time-input" />
                    </div>
                  </div>
                </div>

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

                <div className="space-y-2">
                  <Label htmlFor="budget" className="text-base font-medium">Budget Range (₹)</Label>
                  <Select value={formData.budget_range} onValueChange={(value) => setFormData({ ...formData, budget_range: value })}>
                    <SelectTrigger className="text-lg h-12" data-testid="budget-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="free">Free (₹0)</SelectItem>
                      <SelectItem value="low">Low (₹1 - ₹500)</SelectItem>
                      <SelectItem value="medium">Medium (₹500 - ₹1500)</SelectItem>
                      <SelectItem value="high">High (₹1500+)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {(formData.indoor_outdoor === 'indoor' || formData.indoor_outdoor === 'both') && (
                  <div className="space-y-3">
                    <Label className="text-base font-medium">Available Streaming Services</Label>
                    <div className="grid grid-cols-2 gap-3">
                      {ottOptions.map((ott) => (
                        <div key={ott} className="flex items-center space-x-2">
                          <Checkbox id={ott} checked={formData.ott_subscriptions.includes(ott)} onCheckedChange={(checked) => { if (checked) { setFormData({ ...formData, ott_subscriptions: [...formData.ott_subscriptions, ott] }); } else { setFormData({ ...formData, ott_subscriptions: formData.ott_subscriptions.filter(o => o !== ott) }); } }} data-testid={`ott-${ott.toLowerCase().replace(/\s+/g, '-')}`} />
                          <Label htmlFor={ott} className="cursor-pointer">{ott}</Label>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <Button type="submit" className="w-full rounded-full text-lg h-12 shadow-lg shadow-primary/20" disabled={loading} data-testid="create-group-submit-btn">
                  {loading ? 'Creating Plan...' : (isSoloPlan ? 'Start Planning' : 'Create Group')}
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