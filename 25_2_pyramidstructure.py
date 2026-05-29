l=5
for row in range(1, l+1):
    for column in range(1,row+1):
        print("*",end=" ")
    print()
print("-----------------")

for row in range(1, l+1):
    for column in range(1,row+1):
        print(row,end=" ")
    print()
print("-----------------")

for row in range(1, l+1):
    for column in range(1,row+1):
        print(column,end=" ")
    print()
print("-----------------")

