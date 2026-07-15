#ifndef PMPhysicsList_h
#define PMPhysicsList_h 1

#include "G4VModularPhysicsList.hh"

class PMPhysicsList : public G4VModularPhysicsList
{
public:
    PMPhysicsList();
    virtual ~PMPhysicsList();

    virtual void ConstructProcess() override;
};

#endif