import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { getProfile, updateProfile } from '@/utils/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Slider } from '@/components/ui/slider';
import { Checkbox } from '@/components/ui/checkbox';
import { ArrowLeft, Loader2, Save, User as UserIcon } from 'lucide-react';
import { toast } from 'sonner';

const profileQuestions = [
    { id: 'energy_level', type: 'slider', question: 'Typical Energy Level', min: 1, max: 5, labels: ['Chill', 'Hyper'] },
    { id: 'social_preference', type: 'radio', question: 'Social Style?', options: ['Close Friends', 'New People', 'Mixed', 'Solo'] },
    { id: 'entertainment_primary', type: 'checkbox', question: 'Favorite Entertainment', options: ['Live Events', 'Cinema', 'Gaming', 'Dining', 'Nature', 'Culture'] },
    { id: 'budget_sensitivity', type: 'slider', question: 'Spending Habit', min: 1, max: 5, labels: ['Budget Conscious', 'Money is no object'] },
    { id: 'novelty_seek', type: 'radio', question: 'Novelty?', options: ['Love New Things', 'Stick to Classics', 'Comfort Zone'] },
];

const ProfilePage = () => {
    const navigate = useNavigate();
    const { user, isGuest, setUser } = useAuth(); 
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [formData, setFormData] = useState({ name: '' });
    const [preferences, setPreferences] = useState({});

    useEffect(() => {
        if (isGuest()) {
            navigate('/login');
            return;
        }
        loadProfile();
    }, [isGuest, navigate]);

    const loadProfile = async () => {
        try {
            const response = await getProfile();
            setFormData({ name: response.data.name });
            setPreferences(response.data.default_preferences || {});
        } catch (error) {
            toast.error("Failed to load profile");
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            
            await updateProfile({
                name: formData.name,
                default_preferences: preferences
            });

            const response = await getProfile();

            setUser(response.data);

            toast.success("Profile saved!");
        } catch (error) {
            toast.error("Failed to save profile");
        } finally {
            setSaving(false);
        }
    };

    if (loading) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="animate-spin" /></div>;

    return (
        <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 p-6">
            <div className="max-w-3xl mx-auto py-8">
                <Button variant="ghost" onClick={() => navigate('/dashboard')} className="mb-6">
                    <ArrowLeft className="w-4 h-4 mr-2" /> Back
                </Button>

                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <Card className="glass border-2 mb-8">
                        <CardHeader>
                            <CardTitle className="text-3xl font-outfit font-bold flex items-center gap-3">
                                <UserIcon className="text-primary" /> Edit Profile
                            </CardTitle>
                            <CardDescription>Your preferences are automatically used for new groups.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="space-y-2">
                                <Label>Name</Label>
                                <Input
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="text-lg h-12"
                                />
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="glass border-2">
                        <CardHeader>
                            <CardTitle>Your Default Preferences</CardTitle>
                            <CardDescription>These will be applied automatically when you join a new group.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-8">
                            {profileQuestions.map((q) => (
                                <div key={q.id} className="space-y-3">
                                    <Label className="text-lg font-medium">{q.question}</Label>

                                    {q.type === 'radio' && (
                                        <RadioGroup value={preferences[q.id]} onValueChange={(val) => setPreferences({ ...preferences, [q.id]: val })}>
                                            <div className="flex flex-wrap gap-2">
                                                {q.options.map((opt) => (
                                                    <div key={opt} className="flex items-center space-x-2 glass p-3 rounded-xl cursor-pointer hover:border-primary" onClick={() => setPreferences({ ...preferences, [q.id]: opt })}>
                                                        <RadioGroupItem value={opt} id={`${q.id}-${opt}`} />
                                                        <Label htmlFor={`${q.id}-${opt}`} className="cursor-pointer">{opt}</Label>
                                                    </div>
                                                ))}
                                            </div>
                                        </RadioGroup>
                                    )}

                                    {q.type === 'slider' && (
                                        <div className="space-y-4">
                                            <Slider
                                                value={[preferences[q.id] || 3]}
                                                onValueChange={([val]) => setPreferences({ ...preferences, [q.id]: val })}
                                                min={q.min} max={q.max} step={1}
                                            />
                                            <div className="flex justify-between text-sm text-muted-foreground">
                                                <span>{q.labels[0]}</span>
                                                <span className="font-bold text-primary">{preferences[q.id] || 3}</span>
                                                <span>{q.labels[1]}</span>
                                            </div>
                                        </div>
                                    )}

                                    {q.type === 'checkbox' && (
                                        <div className="flex flex-wrap gap-2">
                                            {q.options.map((opt) => (
                                                <div key={opt} className="flex items-center space-x-2 glass p-3 rounded-xl cursor-pointer" onClick={() => {
                                                    const current = Array.isArray(preferences[q.id]) ? preferences[q.id] : [];
                                                    if (current.includes(opt)) {
                                                        setPreferences({ ...preferences, [q.id]: current.filter(x => x !== opt) });
                                                    } else {
                                                        setPreferences({ ...preferences, [q.id]: [...current, opt] });
                                                    }
                                                }}>
                                                    <Checkbox checked={Array.isArray(preferences[q.id]) && preferences[q.id].includes(opt)} id={`${q.id}-${opt}`} />
                                                    <Label htmlFor={`${q.id}-${opt}`} className="cursor-pointer">{opt}</Label>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}

                            <Button onClick={handleSave} disabled={saving} className="w-full rounded-full h-12 text-lg shadow-lg shadow-primary/20">
                                {saving ? <><Loader2 className="animate-spin mr-2" /> Saving...</> : <><Save className="mr-2 w-5 h-5" /> Save Changes</>}
                            </Button>
                        </CardContent>
                    </Card>
                </motion.div>
            </div>
        </div>
    );
};

export default ProfilePage;